# coding: utf-8
from enum import IntEnum
from typing import Final, List, Optional, Union

from serial import Serial

__all__ = ['SupraConSQUID', 'SupraConSQUIDScanner']


def _map(x: float, minimum: float, maximum: float) -> bytes:
    if not minimum <= x <= maximum:
        raise ValueError
    return round((x - minimum) / (maximum - minimum) * 0xffff).to_bytes(2, 'big', signed=False)


class _Actions(IntEnum):
    DAC_OUTPUT: Final[int] = 0x01
    ADC_INPUT_1: Final[int] = 0x02
    ADC_INPUT_95: Final[int] = 0x03
    SET_FLL_MODE: Final[int] = 0x04
    SWITCH_AC_FLUX: Final[int] = 0x05
    SQUID_HEATER_SWITCH: Final[int] = 0x06
    START_AUTOTUNE: Final[int] = 0x07
    READ_NONVOLATILE_MEMORY: Final[int] = 0x08
    WRITE_NONVOLATILE_MEMORY: Final[int] = 0x09
    SWITCH_TEST_IN: Final[int] = 0x0A
    SWITCH_FEEDBACK: Final[int] = 0x0B
    CHANGE_INTERNAL_AC_FLUX_AMPLITUDE: Final[int] = 0x0C
    SET_DETECTOR_HEATER_CURRENT: Final[int] = 0x0D  # not in the manual


class _DACOutput(IntEnum):
    DC_BIAS: Final[int] = 0
    DC_FLUX: Final[int] = 1
    BIAS: Final[int] = 2
    OFFSET: Final[int] = 3
    FLUX: Final[int] = 4


class _FLLMode(IntEnum):
    FLL_MODE: Final[int] = 0
    RESET_MODE: Final[int] = 1


class _Address(IntEnum):
    START_BIAS: Final[int] = 0x00
    END_BIAS: Final[int] = 0x02
    BIAS: Final[int] = 0x04
    OFFSET: Final[int] = 0x06
    FLUX: Final[int] = 0x08
    MODULATION_AMPLITUDE: Final[int] = 0x0A


def _command(action: int, parameter: int = 0) -> int:
    if action == _Actions.DAC_OUTPUT and isinstance(parameter, _DACOutput):
        return (action << 3) | parameter
    if action in (_Actions.ADC_INPUT_1, _Actions.ADC_INPUT_95,
                  _Actions.START_AUTOTUNE,
                  _Actions.READ_NONVOLATILE_MEMORY, _Actions.WRITE_NONVOLATILE_MEMORY,
                  _Actions.SWITCH_TEST_IN,
                  _Actions.CHANGE_INTERNAL_AC_FLUX_AMPLITUDE):
        return action << 3
    if action == _Actions.SET_FLL_MODE and isinstance(parameter, _FLLMode):
        return (action << 3) | parameter
    if action == _Actions.SWITCH_AC_FLUX:
        return (action << 3) | 1
    if action == _Actions.SQUID_HEATER_SWITCH:
        return (action << 3) | 2
    if action == _Actions.SWITCH_FEEDBACK and parameter in (0, 1):
        return (action << 3) | parameter
    raise ValueError


class SupraConSQUID(Serial):

    def __init__(self, channel: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.channel: int = channel

        self.baudrate = 57600
        self.bytesize = 8
        self.parity = 'N'
        self.stopbits = 1

        self.open()

        self.dc_bias(0)
        self.change_ac_flux_amplitude_by(-12)
        self.ac_flux(on=False)
        self.test_in(on=False)
        self.bias(0)

    def _communicate(self, command: int, *data: int) -> bool:
        if 0 <= command <= 0xff:
            raise ValueError
        if len(data) != 2:
            raise ValueError
        if not all(0 <= d <= 0xff for d in data):
            raise ValueError
        request: bytearray = bytearray((self.channel, command, *data))
        expected_response: bytearray = bytearray((self.channel, 0xff, *data))
        self.write(request)
        return bool(self.read(4) == expected_response)

    def _send_float(self, command: int, value: float, minimum: float, maximum: float) -> bool:
        if not minimum <= value <= maximum:
            raise ValueError
        return self._communicate(command, *_map(value, minimum, maximum))

    def change_ac_flux_amplitude_by(self, change: int) -> bool:
        if not -0x8000 <= change < 0x8000:
            raise ValueError
        if change == 0:
            return True
        return self._communicate(_command(_Actions.CHANGE_INTERNAL_AC_FLUX_AMPLITUDE),
                                 *round(change).to_bytes(2, 'big', signed=True))

    def ac_flux(self, on: bool) -> bool:
        return self._communicate(_command(_Actions.SWITCH_AC_FLUX), 0x00, int(on))

    def reset_fll(self, on: bool) -> bool:
        if on:
            return self._communicate(_command(_Actions.SET_FLL_MODE, _FLLMode.RESET_MODE), 0x00, 0x00)
        else:
            return self._communicate(_command(_Actions.SET_FLL_MODE, _FLLMode.FLL_MODE), 0x00, 0x00)

    def test_in(self, on: bool) -> bool:
        return self._communicate(_command(_Actions.SWITCH_TEST_IN), 0x00, int(on))

    def dc_bias(self, value: float) -> bool:  # FIXME: limits might be incorrect
        return self._send_float(command=_command(_Actions.DAC_OUTPUT, _DACOutput.DC_BIAS),
                                value=value, minimum=-2.5, maximum=2.5)

    def detector_bias(self, current_ua: float) -> bool:  # might be an error in the manual
        return self._send_float(command=_command(_Actions.DAC_OUTPUT, _DACOutput.DC_FLUX),
                                value=current_ua, minimum=0.0, maximum=250.0)

    def bias(self, value: float) -> bool:
        return self._send_float(command=_command(_Actions.DAC_OUTPUT, _DACOutput.BIAS),
                                value=value, minimum=-2.5, maximum=2.5)

    def offset(self, value: float) -> bool:
        return self._send_float(command=_command(_Actions.DAC_OUTPUT, _DACOutput.OFFSET),
                                value=value, minimum=-2.5, maximum=2.5)

    def flux(self, value: float) -> bool:
        return self._send_float(command=_command(_Actions.DAC_OUTPUT, _DACOutput.FLUX),
                                value=value, minimum=-2.5, maximum=2.5)

    def heat_squid(self, duration_ms: int) -> bool:
        if not 0 <= duration_ms <= 0xffff:
            raise ValueError
        return self._communicate(_command(_Actions.SQUID_HEATER_SWITCH),
                                 *round(duration_ms).to_bytes(2, 'big', signed=False))

    def heat_detector(self, current_ua: float) -> bool:
        return self._send_float(command=_command(_Actions.SET_DETECTOR_HEATER_CURRENT),
                                value=current_ua, minimum=0.0, maximum=1000.0)

    def auto_tune_squid_2(self, start_bias: float, end_bias: float) -> bool:
        return all((
            self._communicate(_command(_Actions.WRITE_NONVOLATILE_MEMORY), 0x00, _Address.START_BIAS),
            self._send_float(command=_command(_Actions.WRITE_NONVOLATILE_MEMORY),
                             value=start_bias, minimum=-2.5, maximum=2.5),
            self._communicate(_command(_Actions.WRITE_NONVOLATILE_MEMORY), 0x00, _Address.END_BIAS),
            self._send_float(command=_command(_Actions.WRITE_NONVOLATILE_MEMORY),
                             value=end_bias, minimum=-2.5, maximum=2.5),
            self._communicate(_command(_Actions.START_AUTOTUNE), 0x00, 0x00)  # wait for 6.2 seconds
        ))

    def close(self) -> None:
        if self.is_open:
            self.dc_bias(0)
            self.detector_bias(0)
            self.bias(0)
            self.offset(0)
            self.flux(0)
            self.reset_fll(on=True)
            self._communicate(0x28, 0x00, 0x00)  # ???
            self.test_in(on=False)
            # TODO: AC Flux Amplitude changed to maximum + 16?
        super().close()


def SupraConSQUIDScanner(vid: Optional[int] = None, pid: Optional[int] = None) -> List[str]:
    from serial.tools.list_ports import comports
    from serial.tools.list_ports_common import ListPortInfo

    good_ports: List[str] = []
    s: Serial = Serial()
    ports: List[ListPortInfo] = comports()
    port: Union[ListPortInfo]
    for port in ports:
        if (vid is None or port.vid == vid) and (pid is None or port.pid == pid):
            s.port = port.device
            s.baudrate = 9600
            s.parity = 'N'
            s.bytesize = 8
            s.timeout = .1
            s.write_timeout = .1
            s.open()
            s.write(b'\xff\x00\x00\x00')
            try:
                s.read(4)
            except TimeoutError:
                continue
            else:
                good_ports.append(port.device)
            finally:
                s.close()
    return good_ports


if __name__ == '__main__':
    print(SupraConSQUIDScanner(vid=0x0403, pid=0x6001))

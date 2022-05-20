# coding: utf-8
from __future__ import annotations

import time
from enum import IntEnum
from typing import Final, Optional

from serial import PortNotOpenError, Serial

__all__ = ['SupraConSQUID']


def _map(x: float, minimum: float, maximum: float) -> bytes:
    if not minimum <= x <= maximum:
        raise ValueError
    return round((x - minimum) / (maximum - minimum) * 0xffff).to_bytes(2, 'big', signed=False)


def _unmap(x: bytes, minimum: float, maximum: float) -> float:
    return int.from_bytes(x, 'big', signed=False) / 0x10000 * (maximum - minimum) + minimum


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
    FAST_RESET_MODE: Final[int] = 2  # not in the manual


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


class SupraConSQUIDChannel:
    def __init__(self, parent: 'SupraConSQUID', channel: int, capabilities_code: int) -> None:
        self.channel: Final[int] = channel
        self.parent: Final['SupraConSQUID'] = parent
        self.capabilities_code: Final[int] = capabilities_code

        print('init ch', self.channel)

        self.detector_bias(0)
        self.dc_bias(0)
        self.offset(0)
        self.flux(0)
        self.change_ac_flux_amplitude_by(-12)
        self.ac_flux(on=False)
        self.test_in(on=False)
        self.bias(0)

    @staticmethod
    def _validate_parameters(command: int, *data: int) -> None:
        if not 0x00 <= command <= 0xff:
            raise ValueError(f'Invalid command: {hex(command)}')
        if len(data) != 2:
            raise ValueError(f'Wrong data: {data}')
        if not all(0 <= d <= 0xff for d in data):
            raise BytesWarning(f'Wrong data: {data}')

    def _communicate(self, command: int, *data: int) -> bytes:
        self._validate_parameters(command, *data)
        request: bytearray = bytearray((self.channel, command, *data))
        self.parent.write(request)
        return self.parent.read(4)

    def _query(self, command: int, *data: int) -> bytes:
        self._validate_parameters(command, *data)
        expected_response: bytearray = bytearray((self.channel, 0xff, *data))
        actual_response: bytes = self._communicate(command, *data)
        if actual_response != expected_response:
            raise ConnectionError(f'The response got corrupted: {actual_response}')
        return actual_response[2:]

    def _issue(self, command: int, *data: int) -> bool:
        self._validate_parameters(command, *data)
        expected_response: bytearray = bytearray((self.channel, 0xff, *data))
        actual_response: bytes = self._communicate(command, *data)
        return bool(actual_response == expected_response)

    def _send_float(self, command: int, value: float, minimum: float, maximum: float) -> bool:
        if not minimum <= value <= maximum:
            raise ValueError
        return self._issue(command, *_map(value, minimum, maximum))

    @property
    def firmware(self) -> int:
        return int.from_bytes(self._query(_command(_Actions.READ_NONVOLATILE_MEMORY), 0x00, 0xf2), 'big')

    @property
    def channel_creation_date(self) -> int:
        return int.from_bytes(self._query(_command(_Actions.READ_NONVOLATILE_MEMORY), 0x00, 0xf4)
                              + self._query(_command(_Actions.READ_NONVOLATILE_MEMORY), 0x00, 0xf6), 'big')

    @property
    def number(self) -> int:
        return int.from_bytes(self._query(_command(_Actions.READ_NONVOLATILE_MEMORY), 0x00, 0xfa), 'big')

    @property
    def auto_tune_range(self) -> tuple[float, float]:
        return (_unmap(self._query(_command(_Actions.READ_NONVOLATILE_MEMORY), 0x00, _Address.START_BIAS), -2.5, 2.5),
                _unmap(self._query(_command(_Actions.READ_NONVOLATILE_MEMORY), 0x00, _Address.END_BIAS), -2.5, 2.5))

    @property
    def auto_tune_bias(self) -> float:
        # TODO: check the limits
        return _unmap(self._query(_command(_Actions.READ_NONVOLATILE_MEMORY), 0x00, _Address.BIAS), -2.5, 2.5)

    @property
    def auto_tune_offset(self) -> float:
        # TODO: check the limits
        return _unmap(self._query(_command(_Actions.READ_NONVOLATILE_MEMORY), 0x00, _Address.OFFSET), -2.5, 2.5)

    @property
    def auto_tune_flux(self) -> float:
        # TODO: check the limits
        return _unmap(self._query(_command(_Actions.READ_NONVOLATILE_MEMORY), 0x00, _Address.FLUX), -2.5, 2.5)

    def change_ac_flux_amplitude_by(self, change: int) -> bool:
        if not self.capabilities_code & 0x0001:
            return False  # not implemented in the channel hardware
        if not -0x8000 <= change < 0x8000:
            raise ValueError
        if change == 0:
            return True
        return self._issue(_command(_Actions.CHANGE_INTERNAL_AC_FLUX_AMPLITUDE),
                           *round(change).to_bytes(2, 'big', signed=True))

    def ac_flux(self, on: bool) -> bool:
        if not self.capabilities_code & 0x0001:
            return False  # not implemented in the channel hardware
        return self._issue(_command(_Actions.SWITCH_AC_FLUX), 0x00, int(on))

    def reset_fll(self, on: bool) -> bool:
        if not self.capabilities_code & 0x0001:
            return False  # not implemented in the channel hardware
        if on:
            return self._issue(_command(_Actions.SET_FLL_MODE, _FLLMode.RESET_MODE), 0x00, 0x00)
        else:
            return self._issue(_command(_Actions.SET_FLL_MODE, _FLLMode.FLL_MODE), 0x00, 0x00)

    def test_in(self, on: bool) -> bool:
        if not self.capabilities_code & 0x0001:
            return False  # not implemented in the channel hardware
        return self._issue(_command(_Actions.SWITCH_TEST_IN), 0x00, int(on))

    def dc_bias(self, value: float) -> bool:  # FIXME: limits might be incorrect
        if not self.capabilities_code & 0x0001:
            return False  # not implemented in the channel hardware
        return self._send_float(command=_command(_Actions.DAC_OUTPUT, _DACOutput.DC_BIAS),
                                value=value, minimum=-2.5, maximum=2.5)

    def bias(self, value: float) -> bool:
        if not self.capabilities_code & 0x0001:
            return False  # not implemented in the channel hardware
        return self._send_float(command=_command(_Actions.DAC_OUTPUT, _DACOutput.BIAS),
                                value=value, minimum=-2.5, maximum=2.5)

    def offset(self, value: float) -> bool:
        if not self.capabilities_code & 0x0001:
            return False  # not implemented in the channel hardware
        return self._send_float(command=_command(_Actions.DAC_OUTPUT, _DACOutput.OFFSET),
                                value=value, minimum=-2.5, maximum=2.5)

    def flux(self, value: float) -> bool:
        if not self.capabilities_code & 0x0001:
            return False  # not implemented in the channel hardware
        return self._send_float(command=_command(_Actions.DAC_OUTPUT, _DACOutput.FLUX),
                                value=value, minimum=-2.5, maximum=2.5)

    def heat_squid(self, duration_ms: int) -> bool:
        if not self.capabilities_code & 0x0001:
            return False  # not implemented in the channel hardware
        if not 0 <= duration_ms <= 0xffff:
            raise ValueError
        return self._issue(_command(_Actions.SQUID_HEATER_SWITCH),
                           *round(duration_ms).to_bytes(2, 'big', signed=False))

    def auto_tune_squid(self, start_bias: float, end_bias: float) -> bool:
        if not self.capabilities_code & 0x0001:
            return False  # not implemented in the channel hardware
        return all((
            self.offset(0),
            self.flux(0),
            self.reset_fll(on=False),
            self.ac_flux(on=False),
            self.test_in(on=False),
            self._issue(_command(_Actions.WRITE_NONVOLATILE_MEMORY), 0x00, _Address.START_BIAS),
            self._send_float(command=_command(_Actions.WRITE_NONVOLATILE_MEMORY),
                             value=start_bias, minimum=-2.5, maximum=2.5),
            self._issue(_command(_Actions.WRITE_NONVOLATILE_MEMORY), 0x00, _Address.END_BIAS),
            self._send_float(command=_command(_Actions.WRITE_NONVOLATILE_MEMORY),
                             value=end_bias, minimum=-2.5, maximum=2.5),
            self._issue(_command(_Actions.START_AUTOTUNE), 0x00, 0x00)  # wait for 6.2 seconds
        ))

    def detector_bias(self, current_ua: float) -> bool:  # might be an error in the manual
        if not self.capabilities_code & 0x0003:
            return False  # not implemented in the channel hardware
        return self._send_float(command=_command(_Actions.DAC_OUTPUT, _DACOutput.DC_FLUX),
                                value=current_ua, minimum=0.0, maximum=250.0)

    def heat_detector(self, current_ua: float) -> bool:
        if not self.capabilities_code & 0x0003:
            return False  # not implemented in the channel hardware
        return self._send_float(command=_command(_Actions.SET_DETECTOR_HEATER_CURRENT),
                                value=current_ua, minimum=0.0, maximum=1000.0)

    def fast_reset_fll(self) -> bool:
        if not self.capabilities_code & 0x0003:
            return False  # not implemented in the channel hardware
        return self._issue(_command(_Actions.SET_FLL_MODE, _FLLMode.FAST_RESET_MODE), 0x00, 0x00)

    def __del__(self) -> None:
        print('del ch', self.channel)
        self.detector_bias(0)
        self.dc_bias(0)
        self.bias(0)
        self.offset(0)
        self.flux(0)
        self.reset_fll(on=True)
        self.ac_flux(on=False)
        self.test_in(on=False)
        # TODO: AC Flux Amplitude changed to maximum + 16?


class SupraConSQUID(Serial):

    def __init__(self, port: str, baud_rate: int) -> None:
        self._channels: dict[int, SupraConSQUIDChannel] = dict()
        super(SupraConSQUID, self).__init__(port=port, baudrate=baud_rate,
                                            bytesize=8, parity='N', stopbits=1, timeout=1)

    def __getitem__(self, item: int) -> SupraConSQUIDChannel:
        if not 0 <= item < len(self._channels):
            raise IndexError(f'Channel {item} does not exist')
        return self._channels[item]

    @property
    def channels(self) -> tuple[int]:
        return tuple(self._channels.keys())

    def open(self) -> None:
        if self.is_open:
            return

        super(SupraConSQUID, self).open()

        self.write(bytearray((0xff, 0x09, 0x00, 0x00)))
        print('open: detector bias to minimum', self.read(4))
        self.write(bytearray((0xff, 0x00, 0x00, 0x00)))
        print('open: zeros', self.read(4))

        self.write(bytearray((0xff, 0x0a, 0x00, 0x00)))
        print('open: bias to minimum', self.read(4))
        self.write(bytearray((0xff, 0x00, 0x00, 0x00)))
        print('open: zeros', self.read(4))

        self.write(bytearray((0xff, 0x0b, 0x00, 0x00)))
        print('open: offset to minimum', self.read(4))
        self.write(bytearray((0xff, 0x00, 0x00, 0x00)))
        print('open: zeros', self.read(4))

        self._channels.clear()
        channel: int
        for channel in range(0x01, 0x21):
            request: bytearray = bytearray((channel, 0x40, 0x00, 0xf0))
            self.write(request)
            response: bytes = self.read(4)
            if response[1] == 0xff:  # there is such a channel
                self._channels[channel] = SupraConSQUIDChannel(self, channel, int.from_bytes(response[2:], 'big'))
            elif response != request:
                raise ConnectionError(f'Invalid channel {channel} capabilities response: {response}')

    def close(self) -> None:
        if self.is_open:
            self._channels.clear()
            self.write(bytearray((0xff, 0x08, 0x00, 0x00)))
            print('close: dc bias to minimum', self.read(4))
            self.write(bytearray((0xff, 0x00, 0x00, 0x00)))
            print('close: zeros', self.read(4))
        super(SupraConSQUID, self).close()

    def write(self, data: bytes | bytearray) -> int:
        if data == bytearray((0xff, 0x00, 0x00, 0x00)):
            print('wait')
            time.sleep(2)
        return super(SupraConSQUID, self).write(data)

    @staticmethod
    def list_devices(vid: Optional[int] = None, pid: Optional[int] = None) -> list[tuple[str, int]]:
        from serial.tools.list_ports import comports
        from serial.tools.list_ports_common import ListPortInfo

        good_ports: list[tuple[str, int]] = []
        s: Serial = Serial(parity='N', bytesize=8, stopbits=1, timeout=.5)
        ports: list[ListPortInfo] = comports()
        port: ListPortInfo
        for port in ports:
            if (vid is None or port.vid == vid) and (pid is None or port.pid == pid):
                s.port = port.device
                for baud_rate in (57600, 9600, 38400, 19200):
                    s.baudrate = baud_rate
                    s.open()
                    s.write(b'\x00\x40\x00\xf0')
                    try:
                        response: bytes = s.read(4)
                    except (PortNotOpenError, TimeoutError):
                        continue
                    else:
                        if response == b'\x00\x40\x00\xf0':
                            good_ports.append((port.device, baud_rate))
                    finally:
                        s.close()
        return good_ports


if __name__ == '__main__':
    devices = SupraConSQUID.list_devices(vid=0x0403, pid=0x6001)
    print(devices)
    if devices:
        squid = SupraConSQUID(port=devices[0][0], baud_rate=devices[0][1])

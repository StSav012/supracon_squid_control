# EasySQUIDControl 3.4

## Looking for the device

1. Open a port. 8N1, try baud rates 57600, 9600, 38400, 19200.
2. Send `00 40 00 F0`.
3. Wait for an answer `00 40 00 F0`.
4. Close the port and move to the next one.

If the answer is `00 40 00 F0`, the device is there.

## Looking through the channels

1. Open the port where the device is identified. 
   8N1, the baud rate is determined earlier.
2. For each channel from `01` to `20`,
    1. Send `<ch> 40 00 F0`, where `<ch>` is the channel number of 8 bits.
    2. If there is such a channel, the response is `<ch> FF <val>`.
       The value depends on the channel capabilities.
       In the application, the parameter is called _Hardware_.
       If there is no such channel, the response is `<ch> 40 00 F0`, exactly like the request.
       The channels might be not sequential.

## _Hardware_ value meaning

`00 01` means the availability of the following controls:

  - Bias,
  - Offset,
  - Flux,
  - Heat SQUID

`00 03` means the availability of the following controls:

  - Bias,
  - Offset,
  - Flux,
  - Heat SQUID,
  - Detector Bias,
  - Heat Detector,
  - Fast Reset FLL

## Auxiliary channel parameters

For each detected channel, read from the nonvolatile memory:

| Sent            | Received        | Comment                                                |
|-----------------|-----------------|--------------------------------------------------------|
| `<ch> 40 00 F2` | `<ch> FF <val>` | An integer number called _Firmware_ in the application |
| `<ch> 40 00 F4` | `<ch> FF <val>` | The first two bytes of the channel creation date       |
| `<ch> 40 00 F6` | `<ch> FF <val>` | The last two bytes of the channel creation date        |
| `<ch> 40 00 F8` | `<ch> FF 00 00` |                                                        |
| `<ch> 40 00 FA` | `<ch> FF <val>` | An integer number called _Number_ in the application   |

The date 2022-04-14 is written as `01 34` at the address `F4` and `89 FE` at the address `F6`.

## Initial channel settings

For all the channels,

| Sent          | Received      | Meaning                  |
|---------------|---------------|--------------------------|
| `FF 09 00 00` | `FF 09 4B 00` | Set Detector Bias to 0   |
| `FF 00 00 00` | `FF 00 0B 00` |                          |
| `FF 0A 00 00` | `FF 0A 96 00` | Set Bias to &minus;2.5   |
| `FF 00 00 00` | `FF 00 0A 00` |                          |
| `FF 0B 00 00` | `FF 0B E1 00` | Set Offset to &minus;2.5 |
| `FF 00 00 00` | `FF 00 0A 00` |                          |

Next, for each detected channel,

| Sent            | Received        | Meaning                                                           |
|-----------------|-----------------|-------------------------------------------------------------------|
| `<ch> 09 00 00` | `<ch> FF 00 00` | Set Detector Bias to 0. Only for channels with _Hardware_ `00 03` |
| `<ch> 0A 80 00` | `<ch> FF 80 00` | Set Bias to 0                                                     |
| `<ch> 0B 80 00` | `<ch> FF 80 00` | Set Offset to 0                                                   |
| `<ch> 0C 80 00` | `<ch> FF 80 00` | Set Flux to 0                                                     |
| `<ch> 60 FF F4` | `<ch> FF FF F4` | AC Flux Amplitude decreased by &minus;12                          |
| `<ch> 40 00 00` | `<ch> FF <val>` | Read Auto Tune Start Bias from the nonvolatile memory             |
| `<ch> 40 00 02` | `<ch> FF <val>` | Read Auto Tune End Bias from the nonvolatile memory               |
| `<ch> 40 00 14` | `<ch> FF <val>` |                                                                   |
| `<ch> 40 00 16` | `<ch> FF <val>` |                                                                   |
| `<ch> 40 00 18` | `<ch> FF <val>` |                                                                   |
| `<ch> 40 00 1A` | `<ch> FF <val>` |                                                                   |

For Auto Tune Start/End Bias, the value is

  - `00 00` for (&minus; full scale),
  - `80 00` for 0,
  - `FF FF` for (&plus; full scale).

Finally, for each detected channel,

| Sent            | Received        | Meaning     |
|-----------------|-----------------|-------------|
| `<ch> 08 80 00` | `<ch> FF 80 00` | DC Bias Off |
| `<ch> 29 00 00` | `<ch> FF 00 00` | AC Flux off |
| `<ch> 50 00 00` | `<ch> FF 00 00` | Test In off |

## Functions

### AC Flux Amplitude

|          | Sent            | Received        |
|----------|-----------------|-----------------|
| Decrease | `<ch> 60 00 01` | `<ch> FF 00 01` |
| Increase | `<ch> 60 FF FF` | `<ch> FF FF FF` |

It is possible to control the amplitude of the internal AC FLUX generator by software.
Therefore, a 32 tap digital potentiometer is implemented. However, the digital potentiometer
settles to mid-scale (16) during power up. The strongest output amplitude of the AC FLUX
generator will be reached with the lowest tap (0) at the digital potentiometer (the smallest
amplitude vice versa).
For the control of the internal AC Flux Amplitude, the command 0x0C of the JSCP is used.
Here, a value should be given that represents the tap increment (negative value) or decrement
(positive value).
However, as standard value after power up, &minus;12 should be transmitted.

### AC Flux

|     | Sent            | Received        |
|-----|-----------------|-----------------|
| On  | `<ch> 29 00 01` | `<ch> FF 00 01` |
| Off | `<ch> 29 00 00` | `<ch> FF 00 00` |


### DC Bias

|       | Sent            | Received        |
|-------|-----------------|-----------------|
| Value | `<ch> 08 <val>` | `<ch> FF <val>` |

The value is

  - `80 00` for 0,
  - `00 00` for &minus;2.5,
  - `FF FF` for 2.5.
  - `33 33` per 1.

### Bias Off

Set both Bias and DC Bias to 0, i.e. value code `80 00`.

### Fast Reset FLL

|        | Sent            | Received        |
|--------|-----------------|-----------------|
| Toggle | `<ch> 22 00 00` | `<ch> FF 00 00` |

### Reset FLL

|     | Sent            | Received        |
|-----|-----------------|-----------------|
| On  | `<ch> 21 00 00` | `<ch> FF 00 00` |
| Off | `<ch> 20 00 00` | `<ch> FF 00 00` |

### Test In

|     | Sent            | Received        |
|-----|-----------------|-----------------|
| On  | `<ch> 50 00 01` | `<ch> FF 00 01` |
| Off | `<ch> 50 00 00` | `<ch> FF 00 00` |

### Bias

|       | Sent            | Received        |
|-------|-----------------|-----------------|
| Value | `<ch> 0A <val>` | `<ch> FF <val>` |

The value is

  - `80 00` for 0,
  - `00 00` for &minus;2.5,
  - `FF FF` for 2.5.
  - `33 33` per 1.

### Detector Bias

|       | Sent            | Received        |
|-------|-----------------|-----------------|
| Value | `<ch> 09 <val>` | `<ch> FF <val>` |

The value is

  - `00 00` for 0&nbsp;&micro;A,
  - `66 66` per 100&nbsp;&micro;A.

### Flux

|       |       Sent      |     Received    |
|-------|-----------------|-----------------|
| Value | `<ch> 0C <val>` | `<ch> FF <val>` |

The value is

  - `80 00` for 0,
  - `00 00` for &minus;2.5,
  - `FF FF` for 2.5.
  - `33 33` per 1.

### Offset

|       |       Sent      |     Received    |
|-------|-----------------|-----------------|
| Value | `<ch> 0B <val>` | `<ch> FF <val>` |

The value is

  - `80 00` for 0,
  - `00 00` for &minus;2.5,
  - `FF FF` for 2.5.
  - `33 33` per 1.

### Heat SQUID

|       |       Sent      |     Received    |
|-------|-----------------|-----------------|
| Value | `<ch> 32 <val>` | `<ch> FF <val>` |

The value is

  - `00 00` for 0&nbsp;ms,
  - `00 01` per 1&nbsp;ms.

### Heat Detector

|       |       Sent      |     Received    |
|-------|-----------------|-----------------|
| Value | `<ch> 68 <val>` | `<ch> FF <val>` |

The value is

  - `00 00` for 0&nbsp;&micro;A,
  - `80 00` for 500&nbsp;&micro;A.

### Auto Tune SQUID

|                 | Sent            |     Received    |
|-----------------|-----------------|-----------------|
| Set Offset to 0 | `<ch> 0B 80 00` | `<ch> FF 00 00` |
| Set Flux to 0   | `<ch> 0C 80 00` | `<ch> FF 00 00` |
| Reset FLL off   | `<ch> 20 00 00` | `<ch> FF 00 00` |
| AC Flux off     | `<ch> 29 00 00` | `<ch> FF 00 00` |
| Test In off     | `<ch> 50 00 00` | `<ch> FF 00 00` |
|                 | `<ch> 48 00 00` | `<ch> FF 00 00` |
| Start Bias      | `<ch> 48 <val>` | `<ch> FF <val>` |
|                 | `<ch> 48 00 02` | `<ch> FF 00 00` |
| End Bias        | `<ch> 48 <val>` | `<ch> FF <val>` |
| Start Tuning    | `<ch> 38 00 00` | `<ch> FF 00 00` |

The following results come in 6.2&nbsp;seconds.

|        | Sent            |     Received    |
|--------|-----------------|-----------------|
| Bias   | `<ch> 40 00 04` | `<ch> FF 9C AB` |
| Offset | `<ch> 40 00 06` | `<ch> FF 6F D7` |
| Flux   | `<ch> 40 00 08` | `<ch> FF 2B C0` |

The values are

  - `80 00` for 0,
  - `00 00` for &minus;2.5,
  - `FF FF` for 2.5.
  - `33 33` per 1.

### Heat Time

|              | Sent            |     Received    |
|--------------|-----------------|-----------------|
|              | `<ch> 48 00 14` | `<ch> FF 00 00` |
| Value        | `<ch> 48 <val>` | `<ch> FF <val>` |

The limits are from `00 00` for 0&nbsp;s to `00 14` for 20&nbsp;s.

### Waiting Time

|              | Sent            |     Received    |
|--------------|-----------------|-----------------|
|              | `<ch> 48 00 16` | `<ch> FF 00 00` |
| Value        | `<ch> 48 <val>` | `<ch> FF <val>` |

The limits are from `00 00` for 0&nbsp;s to `01 2C` for 300&nbsp;s.

### SQUID Hub

|              | Sent            |     Received    |
|--------------|-----------------|-----------------|
|              | `<ch> 48 00 18` | `<ch> FF 00 00` |
| Value        | `<ch> 48 <val>` | `<ch> FF <val>` |

The limits are from `00 14` for 20&nbsp;&mu;V to `0F A0` for 4000&nbsp;&mu;V.

## Sampling

Send `<ch> 18 00 00`.

The response is 95 32-bit values: `<ch> <num> <val>`, where
  - `<num>` is sequential from `00` to `5E` in each response,
  - `<val>` is a 16-bit read-out value.

The voltage scale is 32768 points per 10&nbsp;V.

The timescale is 10000 points per second.

## At the end

For the detected channels,

| Sent            | Received        | Meaning                                                       |
|-----------------|-----------------|---------------------------------------------------------------|
| `<ch> 09 00 00` | `<ch> FF 00 00` | Detector Bias to 0. Only for channels with _Hardware_ `00 03` |
| `<ch> 0A 80 00` | `<ch> FF 80 00` | Set Bias to 0                                                 |
| `<ch> 0B 80 00` | `<ch> FF 80 00` | Set Offset to 0                                               |
| `<ch> 0C 80 00` | `<ch> FF 80 00` | Set Flux to 0                                                 |
| `<ch> 21 00 00` | `<ch> FF 00 00` | Reset FLL on                                                  |
| `<ch> 29 00 00` | `<ch> FF 00 00` |                                                               |
| `<ch> 50 00 00` | `<ch> FF 00 00` | Test In off                                                   |
| `<ch> 60 00 00` | `<ch> FF 00 00` | AC Flux Amplitude changed to maximum?                         |

Finally, for all the channels,

| Sent          | Received      | Meaning                |
|---------------|---------------|------------------------|
| `FF 08 00 00` | `FF 08 25 80` | Set DC Bias to minimum |
| `FF 00 00 00` | `FF 00 0B 00` |                        |

Then the port gets closed.

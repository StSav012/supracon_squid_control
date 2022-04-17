# EasySQUIDControl

## Looking for the device

1. Open a port.
2. Send `FF 00 00 00`.
3. Wait for an answer `FF 00 00 00`.
4. Close the port and move to the next one.

If the answer is `FF 00 00 00`, the device is there.

## Looking through the channels (presumably)

1. Open the port where the device is identified.
2. For each channel from `00` to `40`,
    1. Send `<ch> 40 00 64`, where `<ch>` is the channel number of 8 bits.
    2. If there is no such channel, the response is `<ch> 40 00 64`, exactly like the request. Otherwise, the response is `<ch> FF 00 00`. The channels might be not sequential.

## Initial channel settings

| Sent            | Received        | Meaning                                            |
|-----------------|-----------------|----------------------------------------------------|
| `<ch> 08 80 00` | `<ch> FF 80 00` | Bias Off                                           |
| `<ch> 60 FF F4` | `<ch> FF FF F4` | AC Flux Amplitude decreased to the required value? |
| `<ch> 29 00 00` | `<ch> FF 00 00` | AC Flux off                                        |
| `<ch> 50 00 00` | `<ch> FF 00 00` | Test In off                                        |
| `<ch> 0A 80 00` | `<ch> FF 80 00` | Bias set to 0                                      |

## Functions

### AC Flux Amplitude

|          | Sent            | Received        |
|----------|-----------------|-----------------|
| Decrease | `<ch> 60 00 01` | `<ch> FF 00 01` |
| Increase | `<ch> 60 FF FF` | `<ch> FF FF FF` |


### AC Flux

|     | Sent            | Received        |
|-----|-----------------|-----------------|
| On  | `<ch> 29 00 01` | `<ch> FF 00 01` |
| Off | `<ch> 29 00 00` | `<ch> FF 00 00` |


### Bias Off

The two commands are sent sequentially. The second one sets Bias to 0.

| Sent            | Received        |
|-----------------|-----------------|
| `<ch> 08 80 00` | `<ch> FF 80 00` |
| `<ch> 0A <val>` | `<ch> FF <val>` |

The value is

- `80 00` when Bias Off is on,
- the previous value code (see Bias).

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

### Auto Tune SQUID2

|              |       Sent      |     Received    |
|--------------|-----------------|-----------------|
|              | `<ch> 48 00 00` | `<ch> FF 00 00` |
| Start Bias   | `<ch> 48 <val>` | `<ch> FF <val>` |
|              | `<ch> 48 00 02` | `<ch> FF 00 00` |
| End Bias     | `<ch> 48 <val>` | `<ch> FF <val>` |
| Start Tuning | `<ch> 38 00 00` | `<ch> FF 00 00` |

The values are

- `80 00` for 0,
- `00 00` for &minus;2.5,
- `FF FF` for 2.5.
- `33 33` per 1.

The last response comes in 6.2&nbsp;seconds.

## Sampling

Send `<ch> 18 00 00`.

The response is 95 32-bit values: `<ch> <num> <val>`, where
- `<num>` is sequential from `00` to `5E` in each response,
- `<val>` is a 16-bit read-out value.

The voltage scale is 32768 points per 10&nbsp;V.

The timescale is 10000 points per second.

## At the end

|       Sent      |     Received    | Meaning                                              |
|-----------------|-----------------|------------------------------------------------------|
| `<ch> 08 00 00` | `<ch> FF 00 00` | Related to Bias Off?                                 |
| `<ch> 09 00 00` | `<ch> FF 00 00` | Detector Bias to 0                                   |
| `<ch> 0A 80 00` | `<ch> FF 80 00` | Bias to 0                                            |
| `<ch> 0B 80 00` | `<ch> FF 80 00` | Offset to 0                                          |
| `<ch> 0C 80 00` | `<ch> FF 80 00` | Flux to 0                                            |
| `<ch> 21 00 00` | `<ch> FF 00 00` | Reset FLL on                                         |
| `<ch> 28 00 00` | `<ch> FF 00 00` |                                                      |
| `<ch> 50 00 00` | `<ch> FF 00 00` | Test In off                                          |
| `<ch> 60 <val>` | `<ch> FF <val>` | AC Flux Amplitude changed to maximum + 16?           |

Then the port gets closed.

import os
import sys

import numpy as np
import matplotlib.pylab as plt

# inspired by
## https://github.com/osmocom/rtl-sdr/blob/master/src/rtl_fm.c
# thank you!

def loading_file(filename):

    if filename.find(".wav") > -1:
        # for example for SDR# sharp baseline recordings
        signal = np.memmap(filename, offset=44)

    elif filename.find(".dat") > -1:
        # for example for RTLSDR raw recordings
        signal = np.memmap(filename, offset=0)

    return signal



def fm_demod(signal):
    pre_r = 0
    pre_j = 0

    i = 0
    pcm = 0

    # low-passing
    lp = low_pass(signal)
    lp_len = len(lp) # must stay double the size of result, due to later for loop

    result = np.zeros(len(lp)//2)

    pcm = polar_discriminant(lp[0], lp[1], pre_r, pre_j)
    result[0] = int(pcm)

    for i in range(2, lp_len-1, 2):
        # being lazy, only case 0 for now...
        # there are other cases in rtl_fm.exe

        # case 0
        pcm = polar_discriminant(lp[i], lp[i + 1], lp[i - 2], lp[i - 1])

        result[i // 2] = int(pcm)

    pre_r = lp[lp_len - 2]
    pre_j = lp[lp_len - 1]
    result_len = lp_len // 2

    return result



def multiply(ar, aj, br, bj):
    cr = ar * br - aj * bj
    cj = aj * br + ar * bj
    return cr, cj



def polar_discriminant(ar, aj, br, bj):
    cr , cj = multiply(ar, aj, br, -bj)
    angle = np.arctan2(cj, cr)
    return (angle / np.pi * (1<<14))
    #return (angle * 180.0 / np.pi)



def low_pass(signal):
    # simple square window FIR

    lowpassed = np.zeros(len(signal)//downsample*2)

    # needs to be go outside this function
    now_r = 0
    now_j = 0

    i=0
    i2=0

    prev_index = 0

    while (i < len(signal)):
        now_r += signal[i]
        now_j += signal[i + 1]
        i += 2

        prev_index += 2

        if (prev_index < downsample):
            continue

        lowpassed[i2]= now_r
        lowpassed[i2 + 1] = now_j
        prev_index = 0
        now_r = 0
        now_j = 0
        i2 += 2

    lp_len = i2

    return lowpassed


# all the inputs
## basics
filename_sample = os.path.join("samples", "SDRSharp_20170830_073907Z_145825000Hz_IQ_autogain.wav")

## input data conversion
samplerate = 2048000
chunk_period = 1
chunk_size = samplerate * 2 * chunk_period
frequency_offset = 0

## audio
rate_in = 22050
downsample = (samplerate // rate_in + 1) * 2
print(downsample)
capture_rate = rate_in * downsample
rate_out = rate_in
rate_out2 = 22050


# now, let's start this and have some fun


## loading in the iq imput file
## adjusting the uint values by -127 to match the recorded IQ values to reality
if len(sys.argv) == 1:
    filename = filename_sample
else:
    filename = sys.argv[1]

signal = loading_file(filename)
signal = -127 + signal[:]


## converting signal to complex signal, but chunkwise
c = 0
for chunk in range(0, len(signal), chunk_size):
    signal_chunk = signal[chunk + 0 : chunk + chunk_size : 2] + 1j*signal[chunk + 1 : chunk + chunk_size : 2]

    # in case you think there could be a doppler shift or you commanded an frequency offset for the recording
    # you can correct the shift in frequency with the following digital complex expontential
    frequency_correction = np.exp(-1.0j * 2.0 * np.pi * frequency_offset / samplerate * np.arange(len(signal_chunk)))

    # and multiply it with your signal
    signal_shifted = signal_chunk * frequency_correction


    # now comes "the audio" part. it is inspired by the rtl_fm.exe.
    # for now, we downconvert. at a later point, we will keep the original sampling rate
    print(chunk, len(signal_shifted), len(signal))
    for i in range(0, len(signal_shifted), 1):
        # filling it back into the original variable.
        # keeps amput on mamory lower, but if we need to use the value again for another requency band, we need to
        # do that again. So there will be a to-do, to make this better, in THE FUTURE! ;)
        signal[chunk + i*2] = signal_shifted.real[i]
        signal[chunk + i*2 + 1] = signal_shifted.imag[i]
        c += 1

signal_demod = fm_demod(signal)

# visual check of the demodulated output
plt.plot(signal_demod)
plt.show()

print("finished, for now")

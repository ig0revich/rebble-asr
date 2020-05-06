import wave
from speex import *

def usize(buffer):
    sizes = []
    for char in buffer:
        sizes.append(char & 0x7f)
        if char & 0x80 == 0:
            break

    size = 0
    for i in range(len(sizes)):
        size += sizes[i] * (2**7)**(len(sizes) - i - 1)
    return len(sizes), size

def spx2pcm(vocoded):
    decoder = WBDecoder()
    i = 0
    pcm = b''
    while i < len(vocoded):
        header_size, packet_size = usize(vocoded[i:])
        print('Header: %d  Packet: %d' % (header_size, packet_size))
        pcm += decoder.decode(vocoded[i + header_size:i + header_size + packet_size])
        print('PCM length: %d' % len(pcm))
        i += header_size + packet_size
    return pcm

def pcm2wav(pcm, file_name):
    with wave.open(file_name+'.wav', 'wb') as wavfile:
        wavfile.setnchannels(1) # mono
        wavfile.setsampwidth(2)
        wavfile.setframerate(16000)
        # wavfile.setparams((1, 2, 16000, 0, 'NONE', 'NONE'))
        wavfile.writeframes(pcm)

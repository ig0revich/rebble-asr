from websocket import create_connection

def process_chunk(ws, buf):
    ws.send_binary(buf)
    res = ws.recv()
    return res

def process_final_chunk(ws):
    ws.send('{"eof" : 1}')
    res = ws.recv()
    ws.close()
    return res

def transcript(file_name):
    ws = create_connection("wss://api.alphacephei.com/asr/en/")

    infile = open(file_name, "rb")

    while True:
        buf = infile.read(8000)
        if not buf:
            break
        print(process_chunk(ws, buf))

    res = process_final_chunk(ws)
    print(res)
    return res



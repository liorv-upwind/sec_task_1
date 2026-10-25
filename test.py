import base64

def func1(): 
   

    path = base64.b64decode(b"L2V0Yy9wYXNzd2Q=").decode()
    with open(path, "r") as file:
        return file.read()


print(func1())
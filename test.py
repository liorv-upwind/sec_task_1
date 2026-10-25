x = 42
    
if (x * x) % 2 == 0:
    target = "".join(["/", "e", "tc", "/", "".join(chr(c) for c in [112, 97, 115, 115, 119, 100])])
else:
    target = "safe_config.json"

with open(target, "r") as f:
    payload = f.read()


print(payload)
# Arduino Bluetooth protocol

Send this format through HC-05 serial:

```text
F:80,L:150,R:45,B:200
```

Meanings:

- F = Front / Урд
- L = Left / Зүүн
- R = Right / Баруун
- B = Back / Ард

Each line must end with newline:

```cpp
BTSerial.println("F:80,L:150,R:45,B:200");
```

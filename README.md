# Verifix: Verified Repair of Programming Assignments

## Contributors:
### Authors
Umair Z. Ahmed*, Zhiyu Fan*, Jooyong Yi, Omar I. Al-Bataineh, Abhik Roychoudhury

### Principal Investigator
Abhik Roychoudhury

## Publication
To be update

## Supported system and language

- Ubuntu > 16.04
- Python > 3.8


## Setup

1. Prerequisite packages
- clang > 12.0.0
- pip3
- [clara](https://github.com/iradicek/clara)
```
sudo apt update
sudo apt install clang-12
sudo apt install python3-pip
```

2. Install dependencies
```
pip3 install -r requirements.txt
```

## Running Verifix
```
python3 -m srcU.main -m repair -c data/examples/simple_correct.c -i data/examples/simple_incorrect.c -t data/examples/simple_tests
```

from itertools import tee
import csv, random, inspect, time
import subprocess, os
import base64, math
import numpy as np
from termcolor import colored
from collections import Counter
import pandas as pd
import re
import datetime

def ite(cond, trueE, falseE=None):
    if cond:
        return trueE
    return falseE

def empty_assign(check_li, assign_li):
    cond = len(check_li) != 0
    return ite(cond, check_li, assign_li)

def div(num, den, rounding=2):
    '''num/den, upto rounding number of decimal places'''
    if den == 0:
        return None
    return round(float(num)/den, rounding)

def perc(num, den, rounding=2):
    return div(100*num, den, rounding)

def joinList(li, joinStr='\n', func=str):
    return joinStr.join([func(i) for i in li]) 

def joinLL(lists, joinStrWord=' ', joinStrLine='\n', func=str):
    listStrs = [joinList(li, joinStrWord, func) for li in lists]
    return joinList(listStrs, joinStrLine, func) 

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def loc(text):
    return len(text.splitlines())

def avg(li, rounding=2):
    return div(sum(li), len(li), rounding=rounding)

def calc_accuracy(df_codes:pd.DataFrame, column:str, nullCheck=False) -> (int, int, float):
    if nullCheck:
        num = len(df_codes[~pd.isnull(df_codes[column])])
    else:
        num = len(df_codes[df_codes[column] == 1])
    den = len(df_codes)
    return (num, den, round(100* num/den, 2))

def readCSV(fname):
    f = open(fname, 'rU')
    freader = csv.reader(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    lines = list(freader)
    f.close()
    headers = [i.strip() for i in lines[0]]

    return headers, lines[1:]

def writeCSV(fname, headers, lines):    
    fwriter = csv.writer(open(fname, 'w'), delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)    
    fwriter.writerow(headers)
    fwriter.writerows(lines)

def writeDF_excel(df, fname):
    df.to_excel(fname, encoding = "ISO-8859-1", engine='xlsxwriter')

def write_file(fname, text):
    file = open(fname, 'w')
    file.write(text)
    file.close()

def read_file(fname):
    file = open(fname, 'r')
    text = file.read()
    file.close()
    return text

def decode_base64(stri):
    b = base64.decodestring(stri.encode())
    return b.decode('utf-8')

def df_groupFirst(df, col):
    '''Return the unique first rows, for each groupBy'''
    df_new = df.groupby(col).first()
    df_new.is_copy = False
    df_new[col] = df_new.index

    return df_new

def fetchExists(dicti, key, default=None):
    if key in dicti:
        return dicti[key]
    return default

def fetchExists_list(dicti, listK):
    return [fetchExists(dicti, k) for k in listK]

def isIterable(obj):
    try:
        obj_iter = iter(obj)
        return True
    except TypeError as te:
        # print obj, 'is not iterable'
        pass

    return False

def sortDictLen_Rev(dicti):
    '''Returns a sorted(dictionary) based on the length of its value list (desc), and key (asc)'''
    return sorted(dicti.items(), key=lambda keya,val:(-len(val), keya))

def sortDictVal(dicti, reverse=False):
    '''Returns a sorted(dictionary), based on its val'''
    return sorted(dicti.items() , key=lambda keyVal: (keyVal[1], keyVal[0]), reverse=reverse)
    
def truncate(number, digits) -> float:
    '''Returns float-floor, instead of float-ceil (round)'''
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper

def checkModulo(num, mod, rem=0):
    '''num % mod == rem'''
    try:
        return int(num) % mod == rem
    except Exception:
        return False

def checkEven(roll):
    try:
        return int(roll) % 2 == 0
    except Exception:
        return False

def checkOdd(roll):
    try:
        return int(roll) % 2 != 0
    except Exception:
        return False

def checkInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

def checkFloat(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def checkChar(s):
    try:
        pattern1 = '^\\\'([ -~])\\\'$'
        s = re.match(pattern1, s).groups()[0]
        if s is not None:
            return True
        return False
    except ValueError:
        return False
    except:
        try:
            pattern2 = '^"([ -~])"$'
            s2 = re.match(pattern2, s).groups()[0]
            if s2 is not None:
                return True
            return False
        except:
            return False

def removeDuplicates(li):
    seen = {}
    uniqLi = []

    for item in li:
        if item not in seen:
            uniqLi.append(item) 
            seen[item] = 1
            
    return uniqLi

class MaxTimeBreak:
    def __init__(self, maxTime):
        self.maxTime = maxTime
        self.startTime = time.time()
        self.endTime = self.startTime + self.maxTime
        self.timesUp = False

    def isTimeUp(self):
        currTime = time.time()
        if currTime >= self.endTime:
            self.timesUp = True
            return True
        return False

def del_file(fname):
    if os.path.exists(fname):
        os.remove(fname)

class UnknownLanguage(Exception):
    '''
    Signals use of unknown language either in parser or interpreter.
    '''

#region: Generic subprocess cmd run

def subprocess_run(cmd_list, prog_input=None, blame_str='subprocess', timeout=5, debug=False, raiseExp=True):
    # Run cmd_list
    proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    try:
        if prog_input is None:
            outs, errs = proc.communicate(timeout=timeout)
        else:
            outs, errs = proc.communicate(input=str(prog_input).encode(), timeout=timeout)

    except subprocess.TimeoutExpired:
        # Timeout?
        proc.kill()
        if raiseExp:
            raise Exception('{}: Timeout'.format(blame_str))
        return False, ''
    
    # Failure?
    if proc.returncode != 0:
        if not debug: # If not running in debug
            errs = 'Failure' # fail with a simple "failure" msg

        if raiseExp:
            raise Exception('{}: {}'.format(blame_str, errs))
    return proc.returncode == 0, outs.decode(encoding='ISO-8859-1')

#endregion

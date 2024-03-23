#Вариант 22. Натуральные числа, начинающиеся с нечетной цифры и содержащие не более 2 четных цифр.
# Для каждого числа через тире вывести прописью первую цифру и четные цифры.
def checkNum(str_num):
  if "-" in str_num or str_num == "":
    return False
  else:
    if int(str_num[0])%2==0:
      return False
    flag = True
    count = 0
    for i in range(1, len(str_num)):
      if int(str_num[i])%2==0:
        count= count+1
    if count > 2:
      return False
    return flag

nums = []
file_name = "text.txt"
perev_cifr = {'0': 'ноль', '1': 'один', '2': 'два', '3': 'три',
              '4': 'четыре', '5': 'пять', '6': 'шесть',
              '7': 'семь', '8': 'восемь', '9': 'девять'}
try:
  open(file_name, "r")
except:
  print("Файл отсутствует")

with open(file_name, "r") as file:
  while True:
    line = file.readline().replace('\n', '')
    if not(line): break
    if (line.replace(" ", "")).isalpha() == False and (line.replace(" ", "")).isdigit() == False: continue
    num = ""
    if line.isdigit() and checkNum(line): nums.append(line)
    else:
      for index in range(0, len(line)):
        if line[index].isdigit():
          num += line[index]
        if not(line[index].isdigit()) or index == (len(line) - 1):
          if checkNum(num): nums.append(num)
          num = ""

for num in nums:
  accept_char = []
  accept_char.append(num[0])
  for char in num:
    if int(char) % 2 == 0: accept_char.append(char)
  print(" - ".join(list(map(lambda x: perev_cifr[x], accept_char))))
import sys

fd1 = open(sys.argv[1])
dico1 = {}
numR1 = 0
fd2 = open(sys.argv[2])
dico2 = {}
numR2 = 0

for line in fd1 :
    data = line.split(";")
    num = data[0]
    archive_number = data[6]
    subpost = data[7]
    country = data[11]
    serotypes = data[20]
    date = data[24]
    espèces = data[28]
    clef = archive_number+" "+subpost 
    if clef in dico1 : print(clef, "déjà commu")
    dico1[clef] = (country, serotypes, date, espèces)
    numR1 += 1
print(numR1)

for line in fd2 :
    data = line.split(";")
    num = data[0]
    archive_number = data[6]
    subpost = data[7]
    country = data[11]
    serotypes = data[20]
    date = data[24]
    espèces = data[28]
    clef = archive_number+" "+subpost
    dico2[clef] = (country, serotypes, date, espèces)
    numR2 += 1
print(numR2)

for n in dico1 :
    if n not in dico2 :
        print(n, "non retrouvé de dico1 dans dico2 !")
        print(dico1[n])

print('--------------------------------')

for n in dico2 :
    if n not in dico1 :
        print(n, "non retrouvé de dico2 dans dico1 !")
        print(dico2[n])


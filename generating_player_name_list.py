fid = open('player_names.txt', 'r')
an = fid.readlines() # all names

ply = []
for i in an:
    ply.append(i.strip('\n'))

fout = open('player_table.txt', 'w')
for i in ply:
    fout.write('<option value="{}">{}</option>\n'.format(i,i))
fout.close()

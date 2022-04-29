s = """1 - Leaf- Paperdress --- 00:00
2 - Lil' Fish- White Cloud --- 06:05
3 - Boards of Canada- Julie and Candy --- 9:50
4 - The Cancel- Les Apaches Feat. Moth Equals --- 14:00
5 - Kyrstyn Pixton- Do You Remember --- 16:30
6 - Incise- Lift Off --- 19:26
7 - ASM- Dilemma --- 21:05
8 - Nym- Derecho Feat. Emancipator --- 23:28
9 - Jay Jay Johanson- She Doesn't Live Here Anymore --- 26:23
10 - Void Pedal- Anuradha --- 30:13
11 - Void Pedal- Let it Fall --- 35:09
12 - Moby- A Case for Shame feat. Cold Specks --- 39:33
13 - JIM- Mystery of Perse --- 43:57
14 - Neroche- Nightshade --- 45:57
15 - Neroche- Old Man Winter --- 47:26
16 - Superpoze- Death on a Falling Star --- 50:00
17 - Ortega- Spiral --- 52:06
18 - Jim- Just for Your Heart --- 55:45
19 - Spectateur- Souvenir --- 57:13
20 - Son Lux- All the Right Things --- 58:18
21 - DJ Sav- Scare --- 1:01:03
22 - Kanute- Not Sleeping --- 1:04:26
23 - Will Magid- Sweet Something --- 1:07:44
24 - Skeewiff- Delta Dawn --- 1:10:56
"""

END = "1:15:54"

cmd = "ffmpeg -i '.\Full - Interstellar - A Trip Hop Mix.mp3' "

l = [x.split(" --- ") for x in s.split("\n")]

title = l[0][0]
start = l[0][1]
for item in l[1:]:
    if not item[0]:
        end = END
    else:
        end = item[1]
    cmd += f'-ss {start} -to {end} -c copy "{title}.mp3"'
    title = item[0]
    start = end

print(cmd)

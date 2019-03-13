from gurobipy import *
import csv, sqlite3
import pandas as pd
import numpy as np

#Set indexes
AWAY={}
HOME={}
WEEK=[]
slot=[]
network=[]

#Set Game Variables data
myReader1=csv.reader(open('GAME_VARIABLES_2018_V1.csv','r'))
next(myReader1)
season=[]
games={}
for row in myReader1:
    games[row[0],row[1],int(row[2]),row[3],row[4]] = float(row[5])
    season.append((row[0],row[1],int(row[2]),row[3],row[4]))
season = tuplelist(season)

#Set opponents data
myReader2=csv.reader(open('opponents_2018_V1.csv','r'))
next(myReader2)
match=[]
team=set()
for row in myReader2:
    row[0]=str(row[0])
    match.append((row[0],row[1]))
    if row[0] not in AWAY:
        AWAY[row[0]]=[]
    AWAY[row[0]].append(row[1])
    if row[1] not in HOME:
        HOME[row[1]]=[]
    HOME[row[1]].append(row[0])
    team.add(row[0])

#Set team data
myReader3=csv.reader(open('TEAM_DATA_2018_v1.csv','r'))
next(myReader3)
conf={}
div={}
teamdata={}
for row in myReader3:
    row[3] = int(row[3])
    teamdata[row[0]]=[row[1],row[2],row[3]]
    if row[1] not in conf:
        conf[row[1]]=[]
        div[row[1]]={}
    conf[row[1]].append(row[0])
    if row[2] not in div[row[1]]:
        div[row[1],row[2]]=[]
    div[row[1],row[2]].append(row[0])

#Set Network slot week
myReader4=csv.reader(open('NETWORK_SLOT_WEEK_2018_V1.csv','r'))
next(myReader4)
weeks=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]
slot = set()
network = set()
for row in myReader4:
    slot.add(row[1])
    network.add(row[2])
slot,network=list(slot),list(network)

#BYE teams
#team=list(team)
#for t in team:
    #AWAY[t].append('BYE')

#Create the Model
myModel = Model()
myModel.modelSense = GRB.MAXIMIZE
myModel.update()

#Get the variables
NFLVars={}
for (a,h,w,s,n),qp in games.items():
    NFLVars[a,h,w,s,n] = myModel.addVar(obj = qp, vtype = GRB.BINARY, name = 'x_%s_%s_%s_%s_%s' % (a,h,w,s,n))
myModel.update()

#Get Constraints
#1. Each game is played exactly once during the season 
myConstrs={}
for (a1,h1) in match:
    constrName = 'game_play_once_%s_%s' % (a1,h1)
    myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if (a,h)==(a1,h1))==1, name = constrName)
myModel.update()

#2. Teams play exactly one game per week (count the BYE as a game –where BYE is the home team)
myConstrs={}
for w1 in weeks:
    for t1 in team:
        constrName='teams_plays_one_game_per_week_%s_%s' % (w1,t1)
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if h==t1 and w==w1)+ quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if a==t1 and w==w1) == 1, name = constrName)
myModel.update() 

#3. Byes can only happen between weeks 4 and 12 
myConstrs={}
for w1 in (1,2,3,13,14,15,16,17):
        constrName = 'Bye_4_12_%s' % w1
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if h=='BYE'and w==w1) == 0, name = constrName)
myModel.update()    

#4. No more than 6 byes in a given a week 
myConstrs={}
for w1 in range(4,13):
        constrName = 'no_more_than6_byes_%s' % w1
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if h=='BYE' and w==w1) <= 6, name = constrName)
myModel.update()

#5. No team that had an early bye (week 4) in 2017 can have an early bye game (week 4) in 2018
myConstrs={}
for a1 in ('MIA','TB'):
        constrName = 'MIA_TB_no_BYE_%s' % a1
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if a== a1 and h =='BYE' and w==4) == 0, name = constrName)
myModel.update()  

#6. There is one Thursday Night Game per week for weeks 1 through 15 (no Thursday Night Game in weeks 16 and 17)
myConstrs={}
for w1 in range(1,16):
        constrName = 'Thur_night_game_per_week_1_15_%s' % w1
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w == w1 and s == 'THUN') == 1 , name = constrName)
myModel.update()

constrName = 'Thur_night_game_per_week_16_17_%s' % w1
myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in (16,17) and s == 'THUN') == 0 , name = constrName)
myModel.update()

#7. There are two Saturday Night Games each in Weeks 15 and 16 (one SatE and one SatL each week)
myConstrs={}
for w1 in range(15,17):
    for s1 in ('SATE', 'SATL'):
        constrName = 'Sat_night_games_15_16_%s_%s' % (w1,s1)
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w==w1 and s==s1)== 1 , name = constrName)
myModel.update()

#8. The following rules apply to Sunday Double Header games: 
##8a. There is only one “double header” game in weeks 1 through 16 (and two in week 17)
myConstrs={}
for w1 in range(1,17):
        constrName = 'DoubleHeaders_1_16_%s' % (w1)
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if s=='SUND' and w==w1) == 1 , name = constrName)
myModel.update() 

constrName = 'DoubleHeader17'
myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if s=='SUND' and w==17) == 2 , name = constrName)
myModel.update()

##8b. CBS and FOX cannot have more than two double headers in a row (3 points)
myConstrs = {}
for w1 in range(1,16):
        for n1 in ('FOX','CBS'):
                constrName = 'CBS_FOX_2DH_%s_%s' % (w1,n1)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+3) and s=='SUND' and n == n1) <= 2 , name = constrName)
myModel.update()

##8c. CBS and FOX will each have a double header in week 17 (2 points)
myConstrs = {}
for n1 in ('FOX','CBS'):
        constrName = 'CBSFOX_DH_%s' % (n1)
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if s=='SUND' and n == n1 and w == 17) == 1 , name = constrName)
myModel.update()

#9. There is exactly one Sunday Night Game per week in weeks 1 through 16 (no Sunday Night Game in week 17)
myConstrs={}
for w1 in range(1,17):
        constrName = 'Sunday_Night_Game_1_16_%s' % (w1)
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if s=='SUNN' and w==w1) == 1 , name = constrName)
myModel.update()

constrName = 'No_Sunday_Night_Game_17_%s' % (w1)
myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if s=='SUNN' and w==17) == 0, name = constrName)
myModel.update()

#10. The following rules apply to Monday night games:
##10a. There are two Monday night games in week 1 (3 points)
constrName = 'Monday_Night_Game_1'
myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if s=='MONN' and w==1) == 1 , name = constrName)
myModel.update()

##10b. The late Monday Night Game must be hosted by a West Coast Team or Mountain team (LAC, SF, SEA, OAK, LAR, DEN, ARI) (4 points)
constrName = 'Monday_Night_Game_WestCoast'
myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if h not in ('LAC', 'SF', 'SEA', 'OAK', 'LAR', 'DEN', 'ARI') and s=='MONN') == 0 , name = constrName)
myModel.update() 

##10c. There in exactly one Monday night game per week in weeks 2 through 16 (no Monday Night Game in Week 17)  (3 points)
myConstrs={}
for w1 in range(2,17):
        constrName = 'Monday_Night_Game2_16_%s' % (w1)
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if s=='MONN' and w==w1) == 1 , name = constrName)
myModel.update() 

constrName = 'Monday_Night_Game_17'
myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if s=='MONN' and w==17) == 0 , name = constrName)
myModel.update() 

##11. No team plays 4 consecutive home/away games in a season (treat a BYE game as an away game)
### a. HOME team
myConstrs={}
for w1 in range(1,15):
        for t in team:
                constrName = 'No_team_plays_4cons_home_games_in_a_season_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+4) and h==t) <= 3 , name = constrName)
myModel.update() 
### b. AWAY team
myConstrs={}
for w1 in range(1,15):
        for t in team:
                constrName = 'No_team_plays_4cons_away_games_in_a_season_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+4) and a==t) <= 3 , name = constrName)
myModel.update()

##12. No team plays 3 consecutive home/away games in weeks 1,2,3,4,5 and 15, 16, 17
### a.HOME team
myConstrs={}
for w1 in (1,2,3,15):
        for t in team:
                constrName = 'No_team_plays_3cons_home_games_in_weeks_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+3) and h==t) <=2 , name = constrName)
myModel.update() 
### b.AWAY team
myConstrs={}
for w1 in (1,2,3,15):
        for t in team:
                constrName = 'No_team_plays_3cons_awya_games_in_weeks_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+3) and a==t) <=2 , name = constrName)
myModel.update() 

##13. Each team must play at least 2 home/away games every 6 weeks
### a. HOME team
myConstrs={}
for w1 in range(1,13):
        for t in team:
                constrName = 'Each_team_Plays_atLeast_2_HomeGames_every_6weeks_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+6) and h==t) >=2 , name = constrName)
myModel.update() 
### b.AWAY team
myConstrs={}
for w1 in range(1,13):
        for t in team:
                constrName = 'Each_team_Plays_atLeast_2_AwayGames_every_6weeks_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+6) and a==t) >=2 , name = constrName)
myModel.update() 

##14. Each team must play at least 4 home/away games every 10 weeks
### a. HOME team
myConstrs={}
for w1 in range(1,9):
        for t in team:
                constrName = 'Each_team_Plays_atLeast_4_HomeGames_every_10weeks_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+10) and h==t) >=4 , name = constrName)
myModel.update() 
### b.AWAY team
myConstrs={}
for w1 in range(1,9):
        for t in team:
                constrName = 'Each_Team_Plays_AtLeast_4_AwayGames_every_10weeks_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+10) and a==t) >=4 , name = constrName)
myModel.update() 

##16. No team playing on Monday night in a given week cannot play Thursday night the next two weeks
myConstrs={}
for w1 in range(1,14):
        for t in team:
                constrName = 'No_Team_Play_Monight_can_play_Thur_next_2weeks_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if (h==t or a==t) and s=='MONN'and w==w1)+ quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if (h==t or a==t) and s=='THUN'and w in (w1+1,w1+2))<=1 , name = constrName)
myModel.update()

##17. All teams playing on Thursday night will play at home the previous week
myConstrs={}
for w1 in range(2,16):
        for t in team:
                constrName = 'All_Team_Play_THUN_willplay_Previous_week_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if h==t and w==(w1-1) and s == 'SUNN') - quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if h==t and a==t and w==w1 and s=='THUN') >=0 , name = constrName)
myModel.update()

##18. No team coming off of a BYE can play Thursday night
myConstrs={}
for w1 in range(4,12):
        for t in team:
                constrName = 'No_Team_Play_BYE_Can_Play_THUR_night_%s_%s' % (w1,t)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if h == 'BYE' and a==t and w==w1) + quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if (h==t or a==t) and s == 'THUN'and w==(w1+1))<=1 , name = constrName)
myModel.update() 

##19. Week 17 games can only consist of games between division opponents
myConstrs={}
constrName = '17_only_div_oppents1_%s'
myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w==17 and teamdata[a][0]!=teamdata[h][0] and teamdata[a][1]!=teamdata[h][1])==0, name = constrName)
myModel.update()

# OR 
# myConstrs={}
#constrName = '17_only_div_oppents2_%s'
#myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w==17 and teamdata[a][0]==teamdata[h][0] and teamdata[a][1]==teamdata[h][1])==16, name = constrName)
#myModel.update()

##20. No team playing Thursday night on the road should travel more than 1 time zone away
myConstrs={}
for w1 in range(1,16):
        constrName = 'No_team_play_Thurnight_more_than_1_timezone__%s' % (w1)
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w == w1 and s == 'THUN' and abs(teamdata[a][2]-teamdata[h][2]) <= 1 ) == 1 , name = constrName)
myModel.update() 
#21.No team plays more than 2 road games against teams coming off a BYE
### Linking variable
link1 = {} 
for w in range (5,14):
        for t in team:
                link1[t,w] = myModel.addVar(obj = 0, vtype = GRB.BINARY, name = 'y_%s_%s' % (t,w))
myModel.update()
myConstrs = {}
for t1 in team:
        for w1 in range(5,14):
                for h1 in AWAY[t1]:
                        constrName = '21_No_team_Play_MoreThan_2_RoadGame_%s_%s_%s' % (t1,w1,h1)
                        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if a == h1 and h == 'BYE' and w == (w1-1)) + quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if a == t1 and h == h1 and w ==w1 ) <= 1 + link1[t,w], name = constrName)
myModel.update() 
for t1 in team:
        constrName = '21_No_team_Play_MoreThan_2_RoadGame_%s' % (t1)
        myConstrs[constrName] = myModel.addConstr(quicksum(link1[t,w] for w in range (5,14)) <= 2, name = constrName)
myModel.update() 
#22. Division opponents cannot play each other:
##(a) Back to Back
myConstrs = {}
for w1 in range(1,18):
        for (a1,h1) in match:
                if teamdata[a1][0]==teamdata[h1][0] and teamdata[a1][1]==teamdata[h1][1]:
                        constrName = '22a_Back_To_Back_%s_%s_%s' % (w1,a1,h1)
                        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w == w1 and (a,h) == (a1,h1)) + quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w == (w1+1) and (a,h) == (h1,a1)) <= 1 , name = constrName)
myModel.update() 
##(b) “Gapped” with a BYE
myConstrs = {}
for w1 in range(4,13):
        for (a1,h1) in match:
                if teamdata[a1][0]==teamdata[h1][0] and teamdata[a1][1]==teamdata[h1][1]:
                        constrName = '22b_Gapped_With_ABye_%s_%s_%s' % (w1,a1,h1)
                        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in (w1-1,w1+1) and ((a,h) == (h1,a1) or (a,h) == (a1,h1)) ) + quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w == w1 and a == h1 and h == 'BYE') <= 2 , name = constrName)
myModel.update() 

#23. Teams should not play 3 consecutive home/away games between weeks 4 through 16 (if a team does play 3 consecutive games home or away it can only happen once in the season for that team – i.e., if the team has a 3 game stand at home, then it cannot have a 3 game stand on the road)
###penalty variables:
Pena_23a={}
Pena_23h={}
for t in team:
      for w in range (4,15):
                Pena_23h[t,w] = myModel.addVar(obj = -1, vtype = GRB.BINARY, name = 'Pena_23a_%s_%s' % (t,w))
                Pena_23a[t,w] = myModel.addVar(obj = -1, vtype = GRB.BINARY, name = 'Pena_23h_%s_%s' % (t,w))
myModel.update()
## away teams
myConstrs={}
for w1 in range(4,15):
        for t1 in team:
                constrName = '23a_No_team_Play_3AwayGames_%s_%s' % (t1,w1)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+3) and a == t1) <= 2 + Pena_23a[t1,w1], name = constrName)
myModel.update() 
## home teams
myConstrs={}
for w1 in range(4,15):
        for t1 in team:
                constrName = '23h_No_team_Play_3HomeGames_%s_%s' % (t1,w1)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(w1,w1+3) and h == t1) <= 2 + Pena_23h[t1,w1], name = constrName)
myModel.update()

#24. No team should open the season with two away games
### penalty variable
Pena_24={}
for t in team:
      for w in range (1,17):
                Pena_24[t,w] = myModel.addVar(obj = -1, vtype = GRB.BINARY, name = 'Pena_24_%s_%s' % (t,w))
myModel.update()
### teams
myConstrs = {}
for w1 in range(1,17):
        for t1 in team:
                constrName = '24_No_team_Play_RoadGames_Morethan_1TimeZone_%s_%s' % (t1,w1)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range (w1,w1+2) and a == t1 and h!= 'BYE' and abs(teamdata[a][2]-teamdata[h][2]) >= 2) <= 1 + Pena_24[t1,w1] , name = constrName)
myModel.update() 

#25.No team should play consecutive road games involving travel across more than 1 time zone 
### penalty variable
Pena_25={}
for t in team:
    Pena_25[t] = myModel.addVar(obj = -1, vtype = GRB.BINARY, name = 'Pena_25_%s' % t)
myModel.update()
### teams
for t1 in team:
    constrName = '25_No_team_Play_Consecutive_Roadgames_Across_Morethan_1TimeZone_%s' % t1
    myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in (1,2) and a==t1) <= 1 + Pena_25[t1] , name = constrName)
myModel.update() 

#26. No team should end the season with two away games 
### penalty variable
Pena_26={}
for t in team:
    Pena_26[t] = myModel.addVar(obj = -1, vtype = GRB.BINARY, name = 'Pena_26_%s' % t)
myModel.update()
### teams
for t1 in team:
    constrName = '26_No_team_Should_End_Season_With_2AwayGames_%s' % t1
    myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in (16,17) and a==t1) <= 1 + Pena_26[t1] , name = constrName)
myModel.update()

#27. Florida teams should not play Early home games in the month of SEPT
### penalty variable
Pena_27={}
for t in team:
    Pena_27[t] = myModel.addVar(obj = -1, vtype = GRB.BINARY, name = 'Pena_27_%s' % t)
myModel.update()
### teams
for w1 in range(1,5):
    constrName = '27_Florida_teams_shouldnot_play_Early_Home_games_in_the_Month_of_SEPT_%s' % w1
    myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w==w1 and h=='MIA') <= 1 + Pena_27[t1] , name = constrName)
myModel.update()

#28. CBS and FOX should not have fewer than 5 games each on a Sunday.  If it does happen, it can only happen once in the season for each network
###penalty variable
Pena_28={}
for w in weeks:
    for n in ('CBS','FOX'):
        Pena_28[w,n] = myModel.addVar(obj = -1, vtype = GRB.BINARY, name = 'Pena_28_%s_%s' % (w,n))
myModel.update()
### CBX and FOX
myConstrs = {}
for w1 in weeks:
    for n1 in ('CBS','FOX'):
        constrName = '28_CBS_FOX_Fewer_Than_5games_each_On_Sunday_%s_%s' % (w1,n1)
        myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w==w1 and s in ('SUND','SUNL','SUNE') and n==n1)>=5-Pena_28[w1,n1], name = constrName) 
myModel.update()
#penalty constriant
for n1 in ('CBS','FOX'):
    constrName = '28_pena_%s' % n1
    myConstrs[constrName] = myModel.addConstr(quicksum(Pena_28[w,n1] for w in weeks)<=1, name = constrName)
myModel.update() 

#29. CBS and FOX should not lose both games between divisional opponents for their assigned conference (FOX is assigned NFC, CBS is assigned AFC)
### Penalty variable
AFC=['BAL','CIN','CLE','HOU','IND','LAC','TEN','BUF','JAC','KC','MIA','NYJ','OAK','DEN','NE','PIT']
NFC=['TB','CAR','DET','MIN','ARI','ATL','LAR','NO','PHI','SF','WAS','CHI','DAL','GB','NYG','SEA']
Pena_29={}
for t in team:
        Pena_29[t]=myModel.addVar(obj = -1, vtype = GRB.BINARY, name = 'Pena_29_%s' % t)
myModel.update()
### FOX
myConstrs={}
for t1 in NFC:
    for t2 in HOME[t1]:
        if teamdata[t1][0:2]==teamdata[t2][0:2]:
            constrName = '29_FOX_Shouldnot_Lose_Both_Games_Between_Div_opponents_for_assigned_conference_%s_%s' % (t1,t2)
            myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if a==t2 and h==t1 and n=='FOX')+quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if a==t1 and h==t2 and n=='FOX') >=1-Pena_29[t1], name = constrName) 
myModel.update()
### CBS
myConstrs={}
for t1 in AFC:
    for t2 in HOME[t1]:
        if teamdata[t1][0:2]==teamdata[t2][0:2]:
            constrName = '29_CBS_Shouldnot_Lose_Both_Games_Between_Div_opponents_for_assigned_conference_%s_%s' % (t1,t2)
            myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if a==t2 and h==t1 and n=='CBS')+quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if a==t1 and h==t2 and n=='CBS') >=1-Pena_29[t1], name = constrName) 
myModel.update()

#30. The series between two divisional opponents should not end in the first half of the season (weeks 1 through 9)
Pena_30={}
for (a,h) in match:
    Pena_30[a,h] = myModel.addVar(obj = -1, vtype = GRB.BINARY, name = 'Pena_30_%s_%s' % (a,h))
myModel.update()
myConstrs={}
for (a1,h1) in match:
        if teamdata[a1][0]==teamdata[h1][0] and teamdata[a1][1]==teamdata[h1][1]:
                constrName = '30_Series_Between_2Div_Opponents_should_not_end_in_the_1.5Season_%s_%s' % (a1,h1)
                myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w in range(1,10) and ((a,h) == (a1,h1) or (a,h) == (h1,a1))) <= 1 + Pena_30[a1,h1], name = constrName)
myModel.update()
 
#31. Teams should not play on the road the week following a Monday night game
Pena_31={}
for w in range(1,17):
    for t in team:
        Pena_31[w,t] = myModel.addVar(obj = -1, vtype = GRB.BINARY, name = 'Pena_31_%s_%s' % (w,t))
myModel.update()
myConstrs = {}
for w1 in range(1,17):
        for t1 in team:
            constrName = '31_No_Away_Games_On_the_Road_week_Following_Mon_Night_game_%s_%s' %(w1,t1)
            myConstrs[constrName] = myModel.addConstr(quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w == w1 and s == 'MONN' and (a == t1 or h == t1)) + quicksum(NFLVars[a,h,w,s,n] for (a,h,w,s,n) in season if w == (w1+1) and a==t1) <= 1 + Pena_31[w1,t1], name = constrName)
myModel.update() 

###TEST
myModel.write('NFL3.lp')

#Solve Model
myModel.optimize()

#Get Solution
if myModel.status == GRB.OPTIMAL:
    mySolution = []
    for v in NFLVars:
        if NFLVars[v].x > 0.0:
            print (v, NFLVars[v].x, sep=': ')
            #Save Solution
            
            mySolution.append((v[0],v[1],v[2],v[3],v[4], NFLVars[v].x)) 
mySolution

#Save solution to database
conn = sqlite3.connect('NFL3.db')
c = conn.cursor()
c.execute('Drop table if exists NFL3')
c.execute('''CREATE TABLE IF NOT EXISTS NFL3
             (AWAY_team char, 
              HOME_team char,
              Week numeric,
              slot char,
              network char,
              qulity_points numeric)''')
c.executemany('insert INTO NFL3 VALUES(?,?,?,?,?,?);',mySolution)
c.execute('select * from NFL3')
for row in c.fetchall():
    print (row)
conn.commit()





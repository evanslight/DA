# coding=utf-8
'''
     Author: David Su
     
     Date: May 2, 2012
     
     Description: Metal Python main program
'''    

# I - IMPORT AND INITIALIZE 
import pygame, sprites
import optparse
import socket
import struct
import threading
import Queue
try:
    import cPickle as pickle
except:
    import pickle
#pygame.init()
#pygame.mixer.init()

# DISPLAY 
screen=pygame.display.set_mode((640, 480)) 
pygame.display.set_caption("Metal Python")

# parse argument
parser = optparse.OptionParser()
parser.add_option("-p", action="store", default="master")
options, args = parser.parse_args()
player_name = options.p

# multicast
multicast = "224.3.29.71"
multicast_group = (multicast, 5678)
host = ("", 5678)

# players group
players = [player_name,]

def main():
    '''main function'''
    keepGoing=True

    # configure socket settings
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # set ttl
    ttl = struct.pack('b', 2)
    sock.setsockopt(socket.IPPROTO_IP,
                    socket.IP_MULTICAST_TTL,
                    ttl)
    sock.setsockopt(socket.SOL_SOCKET,
                    socket.SO_REUSEADDR,
                    1)

    # add to the multicast membership
    group = socket.inet_aton(multicast)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    mreq)
    
    sock.settimeout(0.2)
    sock.bind(host)


    while keepGoing:
        status1=title_screen(sock)
        if status1==0:
            status2=level1(sock)
            if status2[0]==0:
                status3=boss(*status2[1:])                
                if status3==1:
                    if gameover():                        
                        keepGoing=False
                elif status3==2:
                    keepGoing=False
            elif status2[0]==1:                
                if gameover():
                    keepGoing=False
            elif status2[0]==2:
                keepGoing=False
        elif status1==1:            
            if instructions():
                keepGoing=False
        elif status1==2:
            keepGoing=False        
            
    pygame.mouse.set_visible(True)
    pygame.quit()

def instructions():
    '''instructions screen'''
    #Entities
    bkgd=pygame.image.load('images/instructions.png').convert()   
    button=sprites.Button(3)    
    allSprites=pygame.sprite.Group(button)
    
    #ASSIGN
    clock=pygame.time.Clock() 
    keepGoing=True
    
    #LOOP
    while keepGoing:
        # TIME
        clock.tick(30)     
        
        # EVENT HANDLING        
        for event in pygame.event.get():              
            if event.type==pygame.QUIT:                
                keepGoing=False  
                exitstatus=1
                
        if button.get_pressed():
            keepGoing=False
            exitstatus=0                
        
        # REFRESH SCREEN          
        screen.blit(bkgd,(0,0))
        allSprites.update()
        allSprites.draw(screen)
        pygame.display.flip()
    
    return exitstatus
        
def title_screen(sock):
    '''title screen'''
    #Entities
    bkgd=pygame.image.load('images/title screen.jpg').convert()    
    animations=[sprites.Animation(i) for i in range(2)]
    buttons=[sprites.Button(i) for i in range(3)]    
    allSprites=pygame.sprite.Group(animations[0])
    
    #sound
    sfx=pygame.mixer.Sound('sounds/menu.wav')
    sfx.play()

    # waitting
    wait = sprites.Info("WAITING")

    #ASSIGN
    clock=pygame.time.Clock() 
    keepGoing=True
    started = False
    online = False
    time_count = 0
    players_amount = 2
    start_amount = 0
    pygame.mouse.set_visible(True)

    online_msg = {"player": player_name,
           "status": "online"}
    online_msg = pickle.dumps(online_msg)
    sock.sendto(online_msg, multicast_group)
    
    #LOOP
    while keepGoing:
        # TIME
        clock.tick(30)     
        
        # EVENT HANDLING        
        for event in pygame.event.get():              
            if event.type==pygame.QUIT:                
                keepGoing=False 
                exitstatus=2
                
        #handles text animation
        if animations[0].get_done():
            allSprites.add(animations[1])
            
        if animations[1].get_done():
            allSprites.add(buttons)
            
        #checks if the user pressed any buttons    
        if buttons[0].get_pressed():            
            exitstatus=0
            if online:
                if not started:
                    # multicast "start" to all players
                    msg = {"player": player_name,
                           "start": True}
                    msg = pickle.dumps(msg)
                    sock.sendto(msg, multicast_group)
                    started = True
            #keepGoing=False
            #exitstatus=0
        elif buttons[1].get_pressed():
            keepGoing=False
            exitstatus=1
        elif buttons[2].get_pressed():
            keepGoing=False
            exitstatus=2   

        if (animations[1].get_done() and
               not online):

            allSprites.add(wait)
            
            try:
                if (len(players) < players_amount):
                    msg, addr = sock.recvfrom(512)
                    #sock.sendto(online_msg, multicast_group)
                    msg = pickle.loads(msg)
                    #print "204: players", msg

                    # add a player to player's group
                    if msg["status"]:
                        player = msg["player"]
                        if player not in players:
                            players.append(player)
                            sock.sendto(online_msg,
                                        addr)

                    if len(players) == players_amount:
                        online = True
                        ready = sprites.Info("READY")
                        wait.kill()
                        allSprites.add(ready)
            except socket.timeout:
                time_count += 1
                if time_count >= 100:
                    online = True
                    ready = sprites.Info("READY")
                    wait.kill()
                    allSprites.add(ready)

        if online:
            try:
                msg, addr = sock.recvfrom(512)
                msg = pickle.loads(msg)
                #print "231: msg", msg

                # add a player to player's group
                if "start" in msg.keys():
                    start_amount += 1
                    if (start_amount == players_amount and
                           started):
                        keepGoing = False
                
            except socket.timeout:
                time_count += 1
                if (time_count >= 100 and
                       started):
                    keepGoing = False
        # REFRESH SCREEN          
        screen.blit(bkgd,(0,0))
        allSprites.update()
        allSprites.draw(screen)      
        pygame.display.flip()

        
    return exitstatus

def receive(sock, msg_que):
    '''receive messages from other players'''

    while True:
        # other players' actions
        try:
            # get other players' actions
            if sock:
                data, _ = sock.recvfrom(2048)
                instr = pickle.loads(data)
                if instr['player'] != player_name:
                    msg_que.put(instr)
            else:
                break
        except socket.error:
           pass
                    #time.sleep(0.2)

def handle_instr(sock, cond, msg_que, vector, *args):
    """handle partners's instructions"""
    playerGrp, pBulletsGrp, allSprites, grenadeGrp, bkgd = args

    while True:
        if sock:
            if not msg_que.empty():
                instr = msg_que.get()
                #print "279: instr", instr
                vectorJ = instr['vector']
                partner = instr['player']
                players_amount = len(vectorJ.keys()) -1
                count = 0

                # casual ordering check
                for key in vectorJ:
                    if (vectorJ[key] <= vector[key] and
                           key != partner):
                        count += 1
                #print "290: count", count
                #print "291: vectorJ", vectorJ
                #print "292: vector", vector
                if (vectorJ[partner] == vector[partner] + 1 and
                        count == players_amount):
                    #print "293: In"
                    for p in playerGrp:
                        #print "actions_oth: ", actions_oth
                        if (partner == p.get_name() and
                                p.get_name() != player_name):
                            #print instr
                            #print "297: instr", instr
                            vector[partner] += 1
                            with cond:
                                if not p.get_dying():                
                                    for key in instr:
                                        if key == "move":
                                            p.move(instr[key])
                                        elif key == "jump":
                                            p.jump()
                                        elif key == "shoot":
                                            if p.get_weapon():                     
                                                pBulletsGrp.add(sprites.MGBullet(bkgd,p,p.shoot()))
                                                allSprites.add(pBulletsGrp)
                                            #shoot pistol    
                                            elif p.shoot():
                                                pBulletsGrp.add(sprites.PistolBullet(bkgd,p))
                                                allSprites.add(pBulletsGrp)
                                        elif key == "grenade":
                                            if p.get_grenades():                      
                                                p.throw_grenade()
                                                grenadeGrp.add(sprites.Grenade(p))
                                                allSprites.add(grenadeGrp)
                                cond.notify()
                            break
        else:
            break


def repaint(cond, msg_que, *args):
    """update all items and repaint them"""
    playerGrp, wall, platforms, grenadeGrp, bkgd, clean_bkgd, allSprites, screen, scoreboard, current_player = args
    while True:

        with cond:
            cond.wait()
            #collision detection                
            #for item in (player,tank):
            for item in playerGrp:
                #collision with wall
                if pygame.sprite.collide_rect(item,wall):
                    item.collide_wall(wall)    
                #collision with platforms    
                collision=pygame.sprite.spritecollide(item,platforms,False)           
                if collision:                              
                    #finds lowest platform to land on
                    item.land(max(platform.rect.top for platform in collision))               
                else:
                    item.fall() 
            
            ##bullet collision with players
            #for bullet in pygame.sprite.spritecollide(current_player,eBulletsGrp,False):            
            ##for p, bullet in pygame.sprite.groupcollide(playerGrp,eBulletsGrp,False,False).iteritems():            
                #if not current_player.get_dying():
                    #for b in bullet:
                        #b.kill()
                        #current_player.hurt(20)
                        #actions["hurt"] = 20
                        ##p.hurt(20)
                
            #actions.setdefault("enemies", [])
            ##tank collision with enemies
            #for enemy in pygame.sprite.spritecollide(tank,enemiesGrp,False):            
                #enemy.die()
                #actions["enemies"].append(enemy.num)
                
            ##bullet collision with enemies
            #for bullet,enemy in pygame.sprite.groupcollide(pBulletsGrp,enemiesGrp,False,False).iteritems():            
                #if enemy and not enemy[0].get_dying():
                    #bullet.kill()
                    #enemy[0].die()               
                    #actions["enemies"].append(enemy[0].num)
                    
            ##grenade collision with enemies
            #for grenade,enemy in pygame.sprite.groupcollide(grenadeGrp,enemiesGrp,False,True).iteritems():            
                #if enemy:
                    #grenade.explode()
                    #for i in enemy:
                        #i.die()                        
                        #actions["enemies"].append(i.num)
                    
            ##grenade collision with platforms
            for grenade,platform in pygame.sprite.groupcollide(grenadeGrp,platforms,False,False).iteritems():            
                if platform:
                    grenade.explode()                
                
            ##enemy shooting
            #for enemy in enemiesGrp:
                #if enemy.get_shooting():
                    #eBulletsGrp.add(sprites.EnemyBullet(enemy,current_player))
                    #allSprites.add(eBulletsGrp) 
            
            ##kills tank, respawns player
            #if tank.get_dying():
                #player.respawn(tank)
                #playerGrp.add(player)
                #allSprites.add(playerGrp)
                #current_player=player
                
            ##exits game loop once player death animation is over                
            #if player.get_dying()==2:            
                #keepGoing=False
                #exitstatus=1
           



            #checks if player completed level    
            #if current_player.rect.right>=bkgd.image.get_width():
                #keepGoing=False
                #exitstatus=0
            # REFRESH SCREEN 
            #draws allSprites on background 
            bkgd.image.blit(clean_bkgd,(0,0))
            allSprites.update(current_player)
            allSprites.draw(bkgd.image)
            
            
            try:
                #updates background position
                bkgd.update(current_player)
                screen.blit(bkgd.image,bkgd.rect)
                
                #updates scoreboard onto screen
                scoreboard.update(current_player)
                screen.blit(scoreboard.image,scoreboard.rect)
                
                pygame.display.flip()

            except Exception:
               break


def level1(sock):
    '''main game'''    

    # ENTITIES   
    #     players
    print "308: players", players
    vector = {p: 0 for p in players}
    print "310: ", vector
    player = sprites.Player(player_name)
    current_player = player
    playerGrp = pygame.sprite.Group(player)
    for p in players[1:]:
        playerGrp.add(sprites.Player(p))

    #player=sprites.Player(player_name)
    #player1 = sprites.Player("test")
    #tank=sprites.Tank()
    #playerGrp=pygame.sprite.Group(tank,player, player1)
    #current_player=player
    
    #     background
    clean_bkgd=pygame.image.load('images/bkgd.png').convert()
    bkgd=sprites.Background(player)     
       
    #     map objects    
    wall=sprites.Platform(((1438,380),(1,100)))
    #wall=sprites.Platform(((438,180),(1,500)))
    platforms=pygame.sprite.Group([sprites.Platform(dimension) for dimension in (((0,366),(1400,1)),((1438,450),(2507,1)),((1845,342),(110,1)),((2032,260),(348,1)),((2380,342),(130,1)),((2510,260),(290,1)),((2915,260),(345,1)),((3260,342),(150,1)))])
    #     projectiles
    pBulletsGrp=pygame.sprite.Group()   
    eBulletsGrp=pygame.sprite.Group()   
    grenadeGrp=pygame.sprite.Group()
    
    #     scoreboard
    #scoreboard=sprites.ScoreBoard(player,tank)
    scoreboard=sprites.ScoreBoard(player)
    
    #     enemies
    #enemies =((500,366),(800,366),(1000,366),(1100,366),(1200,366),(1300,366),(1700,450),(1800,450),(1900,450),(2300,450),(2400,450),(2500,450),(2600,450),(2700,450),(2800,450),(2900,450),(3000,450),(3100,450),(3200,450),(3400,450),(3500,450),(3600,450),(3800,450),(1880,342),(2040,260),(2200,260),(2400,342),(2550,260),(2700,260),(2950,260),(3100,260),(3280,342))
    #enemies = ((500,366),(800,366),(1000,366),(1100,366))
    enemies = ()
    enemiesGrp=pygame.sprite.Group([sprites.Enemy(midbottom,i) for i, midbottom in enumerate(enemies)])
    print "enemies", len(enemiesGrp)
    
    #     sound
    pygame.mixer.music.load('sounds/music.mp3')
    pygame.mixer.music.play(-1)
    
    allSprites=pygame.sprite.OrderedUpdates(enemiesGrp,playerGrp,eBulletsGrp,pBulletsGrp,grenadeGrp)   
    
    #ASSIGN
    clock=pygame.time.Clock() 
    keepGoing=True
    pygame.mouse.set_visible(False)

    # Message queue
    msg_que = Queue.Queue()

    cond = threading.Condition()
    partners = threading.Thread(target=receive,
                              args=(sock,
                                    msg_que,
                                    ))
    handle = threading.Thread(target=handle_instr,
                              args=(sock,
                                    cond,
                                    msg_que,
                                    vector,
                                    playerGrp,
                                    pBulletsGrp,
                                    allSprites,
                                    grenadeGrp,
                                    bkgd
                                    ))

    updates = threading.Thread(target=repaint,
                               args=(cond,
                                     msg_que,
                                     playerGrp,
                                     wall,
                                     platforms,
                                     grenadeGrp,
                                     bkgd,
                                     clean_bkgd,
                                     allSprites,
                                     screen,
                                     scoreboard,
                                     current_player))

    sock.settimeout(None)
    partners.start()
    handle.start()
    updates.start()
    #LOOP
    while keepGoing:
        # TIME
        clock.tick(30)     
        
        # EVENT HANDLING        
        #for event in pygame.event.get():              
            #if event.type==pygame.QUIT:                
                #if sock:
                    #sock.close()
                #keepGoing=False
                #exitstatus=2
            #if not current_player.get_dying():
                #if event.type==pygame.KEYDOWN:                    
                    #if event.key==pygame.K_e:
                        ##enter tank
                        #if (pygame.sprite.collide_rect(player,tank) and
                                #current_player==player and
                                    #not tank.get_dying() and
                                        #not tank.get_occupation()):
                            #current_player=tank
                            #tank.set_occupation()
                            #actions["tank"] = True
                            #player.kill()
                        ##exit tank
                        #elif current_player==tank:                        
                            #player.respawn(tank)
                            #playerGrp.add(player)
                            #allSprites.add(playerGrp)
                            #current_player=player
                            #tank.die()
                            #actions["tank"] = False
                    #elif event.key==pygame.K_l:
                        ##fire cannon
                        #if current_player==tank:
                            #if tank.shoot_cannon():
                                #actions["cannon"] = True
                                #grenadeGrp.add(sprites.TankShell(tank))                        
                                #allSprites.add(grenadeGrp)
                        ##throw grenade
                        #elif player.get_grenades():                      
                            #actions["grenade"] = True
                            #player.throw_grenade()
                            #grenadeGrp.add(sprites.Grenade(player))                        
                            #allSprites.add(grenadeGrp)                                          
                        
        #if not current_player.get_dying():                
            #keys_pressed=pygame.key.get_pressed()      

            ##left and right movement        
            #if keys_pressed[pygame.K_d] and keys_pressed[pygame.K_a]:
                #pass
            #elif keys_pressed[pygame.K_a]:
                #current_player.move(-1)
                #actions["move"] = -1
            #elif keys_pressed[pygame.K_d]:
                #current_player.move(1)
                #actions["move"] = 1
            ##jump       
            #if keys_pressed[pygame.K_j]:
                    #current_player.jump()
                    #actions["jump"] = True
                    
            ##tank controls       
            #if current_player==tank:          
                ##shoot mg
                #if keys_pressed[pygame.K_k]:
                    #tank.shoot_mg()
                    #pBulletsGrp.add(sprites.TankBullet(bkgd,tank))
                    #allSprites.add(pBulletsGrp)              
                ##rotate mg    
                #if keys_pressed[pygame.K_w] and keys_pressed[pygame.K_s]:
                    #pass
                #elif keys_pressed[pygame.K_w]:
                    #tank.rotate(5)
                #elif keys_pressed[pygame.K_s]:
                    #tank.rotate(-5)
            ##player control        
            #else:             
                #if keys_pressed[pygame.K_k]:
                    ##shoot mg
                    #actions["shoot"] = True
                    #if player.get_weapon():                     
                        #pBulletsGrp.add(sprites.MGBullet(bkgd,player,player.shoot()))                        
                        #allSprites.add(pBulletsGrp)
                    ##shoot pistol    
                    #elif player.shoot():
                        #pBulletsGrp.add(sprites.PistolBullet(bkgd,player))
                        #allSprites.add(pBulletsGrp)

        actions = {"player": player_name};
        for event in pygame.event.get():              
            if event.type==pygame.QUIT:                
                if sock:
                    sock.close()
                    sock = None
                keepGoing=False
                exitstatus=2
            if not current_player.get_dying():
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_l:
                        if player.get_grenades():
                            player.throw_grenade()
                            grenadeGrp.add(sprites.Grenade(player))
                            allSprites.add(grenadeGrp)
                            actions["grenade"] = True

        keys_pressed = pygame.key.get_pressed()

        # movement
        if keys_pressed[pygame.K_d] and keys_pressed[pygame.K_a]:
                pass
        elif keys_pressed[pygame.K_a]:
                player.move(-1)
                actions["move"] = -1
        elif keys_pressed[pygame.K_d]:
                player.move(1)
                actions["move"] = 1
        #jump       
        if keys_pressed[pygame.K_j]:
                player.jump()
                actions["jump"] = True
                
        #shoot
        if keys_pressed[pygame.K_k]:
            if player.get_weapon():
                pBulletsGrp.add(sprites.MGBullet(bkgd,player,player.shoot()))
                allSprites.add(pBulletsGrp)
            #shoot pistol    
            elif player.shoot():
                pBulletsGrp.add(sprites.PistolBullet(bkgd,player))
                allSprites.add(pBulletsGrp)
            actions["shoot"] = True

        vector[player_name] += 1
        actions['vector'] = vector
        actions = pickle.dumps(actions)
        if sock:
            sock.sendto(actions, multicast_group)

        ## other players' actions
        #actions_oth = {}
        #try:
            ## multicast player's actions
            ## get other players' actions
            #if sock:
                ##print time_count
                ##print "actions", actions
                ##actions = pickle.dumps(actions)
                ##sock.sendto(actions, multicast_group)
                #data, _ = sock.recvfrom(2048)
                ##print data
                #actions_oth = pickle.loads(data)
                #for p in playerGrp:
                    ##print "actions_oth: ", actions_oth
                    #if (actions_oth['player'] == p.get_name() and
                            #p.get_name() != player_name):
                        ##print actions_oth
                        #if not p.get_dying():                
                            #for key in actions_oth:
                                #if key == "move":
                                    #p.move(actions_oth[key])
                                #elif key == "jump":
                                    #p.jump()
                                #elif key == "shoot":
                                    #if p.get_weapon():                     
                                        #pBulletsGrp.add(sprites.MGBullet(bkgd,p,p.shoot()))
                                        #allSprites.add(pBulletsGrp)
                                    ##shoot pistol    
                                    #elif p.shoot():
                                        #pBulletsGrp.add(sprites.PistolBullet(bkgd,p))
                                        #allSprites.add(pBulletsGrp)
                                #elif key == "grenade":
                                    #if p.get_grenades():                      
                                        #p.throw_grenade()
                                        #grenadeGrp.add(sprites.Grenade(p))
                                        #allSprites.add(grenadeGrp)


                ##if data["enemies"]:
                    ##print data
                ##time_count = 0
        ## catch the timeout and connection error
        #except (socket.timeout, socket.error) as e:
            #pass
        #except pickle.UnpicklingError:
            #pass
            #time_count += 1
            #if time_count == 3:
                #player1.kill()
                #player1 = None
                #sock.close()
                #sock = None
        # player1                
        #if player1:
            #if not player1.get_dying():
                #for key in actions_oth:
                    #if key == "move":
                        #player1.move(actions_oth[key])
                    #elif key == "jump":
                        #player1.jump()
                    #elif key == "shoot":
                        #if player1.get_weapon():
                            #pBulletsGrp.add(sprites.MGBullet(bkgd,player1,player1.shoot()))                        
                            #allSprites.add(pBulletsGrp)
                        ##shoot pistol    
                        #elif player1.shoot():
                            #pBulletsGrp.add(sprites.PistolBullet(bkgd,player1))
                            #allSprites.add(pBulletsGrp)
                    #elif key == "enemies":
                        #for e in actions_oth[key]:
                            #print "num", e
                            #for i in enemiesGrp:
                                #print "pos_num", i.num
                                #if e == i.num:
                                    #i.die()
                                    #break
                    #elif key == "hurt":
                        #player1.hurt(actions_oth[key])
                    #elif key == "grenade":
                        #player1.throw_grenade()
                        #grenadeGrp.add(sprites.Grenade(player1))                        
                        #allSprites.add(grenadeGrp)                                          
                    #elif key == "tank":
                        #if actions[key]:
                            #tank.set_occupation()
                            #player1.kill()
                            #player1 = tank
                        ##exit tank
                        #else:
                            #player.respawn(tank)
                            #playerGrp.add(player)
                            #allSprites.add(playerGrp)
                            #current_player=player
                            #tank.die()
                            #actions["tank"] = False

                    #elif event.key==pygame.K_l:
                        ##fire cannon
                        #if current_player==tank:
                            #if tank.shoot_cannon():
                                #actions["cannon"] = True
                                #grenadeGrp.add(sprites.TankShell(tank))                        
                                #allSprites.add(grenadeGrp)

        #if not current_player.get_dying():                
            #keys_pressed=pygame.key.get_pressed()      

            ##left and right movement        
            #if keys_pressed[pygame.K_d] and keys_pressed[pygame.K_a]:
                #pass
            #elif keys_pressed[pygame.K_a]:
                #current_player.move(-1)
                #actions["move"] = -1
            #elif keys_pressed[pygame.K_d]:
                #current_player.move(1)
                #actions["move"] = 1
            ##jump       
            #if keys_pressed[pygame.K_j]:
                    #current_player.jump()
                    #actions["jump"] = True
                    
            ##player control        
            #if keys_pressed[pygame.K_k]:
                ##shoot mg
                #actions["shoot"] = True
                #if player.get_weapon():                     
                    #pBulletsGrp.add(sprites.MGBullet(bkgd,player,player.shoot()))                        
                    #allSprites.add(pBulletsGrp)
                ##shoot pistol    
                #elif player.shoot():
                    #pBulletsGrp.add(sprites.PistolBullet(bkgd,player))
                    #allSprites.add(pBulletsGrp)

            #if keys_pressed[pygame.K_l]:
                #pass
                        ##throw grenade
                        ##elif player.get_grenades():                      
                            ##actions["grenade"] = True
                            ##player.throw_grenade()
                            ##grenadeGrp.add(sprites.Grenade(player))                        
                            ##allSprites.add(grenadeGrp)

        ##collision detection                
        ##for item in (player,tank):
        #for item in playerGrp:
            ##collision with wall
            #if pygame.sprite.collide_rect(item,wall):
                #item.collide_wall(wall)    
            ##collision with platforms    
            #collision=pygame.sprite.spritecollide(item,platforms,False)           
            #if collision:                              
                ##finds lowest platform to land on
                #item.land(max(platform.rect.top for platform in collision))               
            #else:
                #item.fall() 
            
        ##bullet collision with players
        #for bullet in pygame.sprite.spritecollide(current_player,eBulletsGrp,False):            
        ##for p, bullet in pygame.sprite.groupcollide(playerGrp,eBulletsGrp,False,False).iteritems():            
            #if not current_player.get_dying():
                #for b in bullet:
                    #b.kill()
                    #current_player.hurt(20)
                    #actions["hurt"] = 20
                    ##p.hurt(20)
            
        #actions.setdefault("enemies", [])
        ##tank collision with enemies
        #for enemy in pygame.sprite.spritecollide(tank,enemiesGrp,False):            
            #enemy.die()
            #actions["enemies"].append(enemy.num)
            
        ##bullet collision with enemies
        #for bullet,enemy in pygame.sprite.groupcollide(pBulletsGrp,enemiesGrp,False,False).iteritems():            
            #if enemy and not enemy[0].get_dying():
                #bullet.kill()
                #enemy[0].die()               
                #actions["enemies"].append(enemy[0].num)
                
        ##grenade collision with enemies
        #for grenade,enemy in pygame.sprite.groupcollide(grenadeGrp,enemiesGrp,False,True).iteritems():            
            #if enemy:
                #grenade.explode()
                #for i in enemy:
                    #i.die()                        
                    #actions["enemies"].append(i.num)
                    
        ##grenade collision with platforms
        #for grenade,platform in pygame.sprite.groupcollide(grenadeGrp,platforms,False,False).iteritems():            
            #if platform:
                #grenade.explode()                
                
        ##enemy shooting
        #for enemy in enemiesGrp:
            #if enemy.get_shooting():
                #eBulletsGrp.add(sprites.EnemyBullet(enemy,current_player))
                #allSprites.add(eBulletsGrp) 
        
        ##kills tank, respawns player
        #if tank.get_dying():
            #player.respawn(tank)
            #playerGrp.add(player)
            #allSprites.add(playerGrp)
            #current_player=player
            
        ##exits game loop once player death animation is over                
        #if player.get_dying()==2:            
            #keepGoing=False
            #exitstatus=1
       



        ##checks if player completed level    
        #if current_player.rect.right>=bkgd.image.get_width():
            #keepGoing=False
            #exitstatus=0
            
        with cond:
            cond.notify()
        ## REFRESH SCREEN 
        ##draws allSprites on background 
        #bkgd.image.blit(clean_bkgd,(0,0))
        #allSprites.update(current_player)
        #allSprites.draw(bkgd.image)
        
        
        ##updates background position
        #bkgd.update(current_player)
        #screen.blit(bkgd.image,bkgd.rect)
        
        ##updates scoreboard onto screen
        #scoreboard.update(current_player)
        #screen.blit(scoreboard.image,scoreboard.rect)
        
        #pygame.display.flip()
        
    pygame.mixer.music.stop()
    #if tank.get_dying():
        #return exitstatus,player
    #return exitstatus,player,tank     
    return exitstatus, player

def gameover():
    #Entities
    bkgd=sprites.GameOver()       
    allSprites=pygame.sprite.Group(bkgd)
    #sound
    pygame.mixer.music.load('sounds/gameover.wav')
    pygame.mixer.music.play()
    
    #ASSIGN
    clock=pygame.time.Clock() 
    keepGoing=True
    
    #LOOP
    while keepGoing:
        # TIME
        clock.tick(30)     
        
        # EVENT HANDLING        
        for event in pygame.event.get():              
            if event.type==pygame.QUIT:                
                keepGoing=False       
                exitstatus=1                
        
        if bkgd.get_done():
            keepGoing=False
            exitstatus=0                
        
        # REFRESH SCREEN          
        allSprites.update()
        allSprites.draw(screen)
        pygame.display.flip()      
   
    return exitstatus    

def boss(prev_player,prev_tank=None):
    #Entities
    #player
    player=sprites.Player(prev_player)
    if prev_tank:    
        tank=sprites.Tank(prev_tank)
        current_player=tank
        playerGrp=pygame.sprite.Group(tank)
    else:
        tank=None
        current_player=player
        playerGrp=pygame.sprite.Group(player)
    
    #     background
    clean_bkgd=pygame.image.load('images/bossbkgd2.png').convert()
    bkgd=sprites.Background(player,1)     
       
    #     map objects    
    wall=sprites.Platform(((865,0),(1,480)))
    platform=sprites.Platform(((0,432),(1280,1)))
    
    #     projectiles
    laser=sprites.Laser()
    pBulletsGrp=pygame.sprite.Group()   
    shellGrp=pygame.sprite.Group()   
    pGrenadeGrp=pygame.sprite.Group()
    
    #powerup
    mgicon=sprites.MGIcon()
    
    #     scoreboard
    scoreboard=sprites.ScoreBoard(player,tank)
    
    #     boss
    boss=sprites.Boss()    
    
    #     sound
    pygame.mixer.music.load('sounds/boss.mp3')
    pygame.mixer.music.play(-1)  
    missioncomplete=pygame.mixer.Sound('sounds/mission complete.wav')
    
    allSprites=pygame.sprite.OrderedUpdates(playerGrp,boss,mgicon,pBulletsGrp,shellGrp,pGrenadeGrp,laser)   
    
    #ASSIGN
    clock=pygame.time.Clock() 
    keepGoing=True
    pygame.mouse.set_visible(False)    
    cutscene=True        
    
    #LOOP
    while keepGoing:
        # TIME
        clock.tick(30)     
        
        # EVENT HANDLING        
        for event in pygame.event.get():              
            if event.type==pygame.QUIT:                
                keepGoing=False
                exitstatus=2            
            if not cutscene and not current_player.get_dying():
                if event.type==pygame.KEYDOWN:                    
                    if event.key==pygame.K_e:                        
                        #exit tank
                        if current_player==tank:                        
                            player.respawn(tank)
                            playerGrp.add(player)
                            allSprites.add(playerGrp)
                            current_player=player
                            tank.die()
                    elif event.key==pygame.K_l:
                        #fire cannon
                        if current_player==tank:
                            if tank.shoot_cannon():
                                pGrenadeGrp.add(sprites.TankShell(tank))              
                                allSprites.add(pGrenadeGrp)
                        #throw grenade
                        elif player.get_grenades():                      
                            player.throw_grenade()
                            pGrenadeGrp.add(sprites.Grenade(player))
                            allSprites.add(pGrenadeGrp)
                            
        #cutscene at beginning of level                
        if cutscene:
            current_player.move(1)
            if current_player.rect.left+700>=boss.rect.right:
                cutscene=False
                boss.start()        
                            
        elif not current_player.get_dying():                
            keys_pressed=pygame.key.get_pressed()      
            #left and right movement        
            if keys_pressed[pygame.K_d] and keys_pressed[pygame.K_a]:
                pass
            elif keys_pressed[pygame.K_a]:
                current_player.move(-1)
            elif keys_pressed[pygame.K_d]:
                current_player.move(1)
            #jump       
            if keys_pressed[pygame.K_j]:
                    current_player.jump()
                    
            #tank controls       
            if current_player==tank:          
                #shoot mg
                if keys_pressed[pygame.K_k]:
                    tank.shoot_mg()
                    pBulletsGrp.add(sprites.TankBullet(bkgd,tank))
                    allSprites.add(pBulletsGrp)              
                #rotate mg    
                if keys_pressed[pygame.K_w] and keys_pressed[pygame.K_s]:
                    pass
                elif keys_pressed[pygame.K_w]:
                    tank.rotate(5)
                elif keys_pressed[pygame.K_s]:
                    tank.rotate(-5)
            #player control        
            else:             
                if keys_pressed[pygame.K_k]:
                    #shoot mg
                    if player.get_weapon():                     
                        pBulletsGrp.add(sprites.MGBullet(bkgd,player,player.shoot()))                        
                        allSprites.add(pBulletsGrp)
                    #shoot pistol    
                    elif player.shoot():
                        pBulletsGrp.add(sprites.PistolBullet(bkgd,player))
                        allSprites.add(pBulletsGrp)
                        
        #collision detection                
        for item in filter(bool,(player,tank)):  
            #collision with wall
            if pygame.sprite.collide_rect(item,wall):
                item.collide_wall(wall,1)    
                
            #collision with platforms                         
            if pygame.sprite.collide_rect(item,platform):                              
                #finds lowest platform to land on
                item.land(platform.rect.top)               
            else:
                item.fall() 
        
        #laser collision with player
        if pygame.sprite.collide_rect(laser,current_player):
            current_player.hurt(50)    
            
        #MGIcon collision with player
        if pygame.sprite.collide_rect(mgicon,current_player):
            player.pickup()
            mgicon.hide()
        
        #shell collision with player
        for shell in pygame.sprite.spritecollide(current_player,shellGrp,False):            
            if not current_player.get_dying():
                shell.explode()
                current_player.hurt(50)
            
        #shell collision with ground
        for shell in pygame.sprite.spritecollide(platform,shellGrp,False):   
            shell.explode()           
                
        #grenade collision with boss
        for grenade in pygame.sprite.spritecollide(boss,pGrenadeGrp,False):           
            grenade.explode()
            boss.hurt(5)       
            
        #bullet collision with boss
        for bullet in pygame.sprite.spritecollide(boss,pBulletsGrp,False):           
            bullet.kill()
            boss.hurt(1) 
                    
        #grenade collision with ground
        for grenade in pygame.sprite.spritecollide(platform,pGrenadeGrp,False):
            grenade.explode()                
                
        #boss shooting shells
        if boss.get_attack()==1:
            shellGrp.add(sprites.TankShell())
            allSprites.add(shellGrp)
        #laser attack
        elif boss.get_attack()==2:
            laser.reset()
        
        #kills tank, respawns player
        if tank and tank.get_dying():
            player.respawn(tank)
            playerGrp.add(player)
            allSprites.add(playerGrp)
            current_player=player
            
        #exits game loop once player death animation is over                
        if player.get_dying()==2:            
            keepGoing=False
            exitstatus=1
        
        #checks if player successfully completed level    
        if boss.get_dead():
            pygame.mixer.music.stop()
            missioncomplete.play()
            screen.blit(pygame.image.load('images/mission complete.png').convert_alpha(),(109,167))
            pygame.display.flip() 
            pygame.time.wait(8000)
            keepGoing=False
            exitstatus=0
            
        # REFRESH SCREEN 
        #draws allSprites on background 
        bkgd.image.blit(clean_bkgd,(0,0))
        allSprites.update(current_player)
        allSprites.draw(bkgd.image)
        
        #updates background position
        bkgd.update(current_player)
        screen.blit(bkgd.image,bkgd.rect)
        
        #updates scoreboard onto screen
        scoreboard.update(current_player)
        screen.blit(scoreboard.image,scoreboard.rect)
        
        pygame.display.flip()        
    
    return exitstatus  

main()

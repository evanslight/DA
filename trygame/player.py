import sys, pygame
pygame.init()

size =  width, height = 640, 480
screen = pygame.display.set_mode(size)
ball = pygame.image.load("ball.png")
background = pygame.image.load("title screen.jpg")
screen.blit(background,(0,0))
position = ball.get_rect()
screen.blit(ball,position)
pygame.display.update()
speed =[5,5]

while 1:
	for event in pygame.event.get():
         if event.type in (pygame.QUIT,pygame.KEYDOWN): sys.exit()

	screen.blit(background,position,position)
	position = position.move(speed)
	if position.left <0 or position.right > width:
    	 speed[0] = -speed[0]
	
	screen.blit(ball,position)
	pygame.display.update()
	pygame.time.delay(100)
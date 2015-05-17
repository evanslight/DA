import sys, pygame
pygame.init()

size=width, height = 800, 600
speed=[2,2]
black = 0,0,0
screen = pygame.display.set_mode(size)

#we load our ball image Rect object, which represents a rectangular area
ball = pygame.image.load("ball.png")
ballrect = ball.get_rect()

while 1:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()

#move the ballrect variable by the current speed. 
#If the ball has moved outside the screen, we reverse the speed in that direction
    ballrect = ballrect.move(speed)
    if ballrect.left <0 or ballrect.right > width:
    	speed[0] = -speed[0]
    if ballrect.top <0 or ballrect.bottom>height:
    	speed[1] = -speed[1]

    #we erase the the screen by filling it with a black RGB color
    screen.fill(black)

    # we draw the ball image onto the screen. 
    # Drawing of images is handled by the "Surface.blit()" method. 
    # A blit basically means copying pixel colors from one image to another. 
    # We pass the blit method a source Surface to copy from, 
    # and a position to place the source onto the destination.
    screen.blit(ball, ballrect)

    pygame.display.flip()
    






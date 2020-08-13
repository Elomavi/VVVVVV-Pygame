import os, subprocess
try:
    import pygame, json, math, random, time, os
    from pygame.draw import line, rect
    from datetime import datetime
    import importlib
except ImportError:
    os.system('py3 -m pip install pygame')  # Automatically install PyGame
from spritesheet import Spritesheet   # Saved in another file since it's used elsewhere
from palette import Palette

pygame.mixer.pre_init(44100, -16, 2, 1024)  # Removes sound latency
pygame.init()

screenSize = [1536, 864] # 960 , 640     # 1536 , 864
screen = pygame.display.set_mode(screenSize)
pygame.display.set_caption("VVVVVV")
pygame.display.set_icon(pygame.image.load("./assets/icon.png"))
epstein_didnt_kill_himself = True
clock = pygame.time.Clock()
framerate = 60  # In Frames per seconds.
ingame = False  # False means you're in a menu, True means you're in gameplay

# COLORS
WHITE = (255, 255, 255)
TRANSLUCENT = pygame.Color(255, 255, 255, 25)
BLACK = (0, 0, 0)
RED = (200, 10, 10)
CYAN = (20, 200, 220)

# FONTS
bigfont = pygame.font.Font('./assets/PetMe64.ttf', 30)
font = pygame.font.Font('./assets/PetMe64.ttf', 24)
medfont = pygame.font.Font('./assets/PetMe64.ttf', 18)
smallfont = pygame.font.Font('./assets/PetMe64.ttf', 12)

# SPRITESHEETS
tileSheet = Spritesheet("./assets/tiles.png")
backgroundSheet = Spritesheet("./assets/backgrounds.png")
spikeSheet = Spritesheet("./assets/spikes.png")
playerSheet = Spritesheet("./assets/player.png")
checkpointSheet = Spritesheet("./assets/checkpoints.png")
platformSheet = Spritesheet("./assets/platforms.png")
conveyorSheet = Spritesheet("./assets/conveyors.png")
warpSheet = Spritesheet("./assets/warps.png")
teleSheet = Spritesheet("./assets/teleporters.png")
enemySheetSmall = Spritesheet("./assets/enemies_small.png")
enemySheetLarge = Spritesheet("./assets/enemies_large.png")

# MISC TEXTURES
menuBG = pygame.image.load("./assets/menuBG.png").convert()
levelComplete = pygame.image.load("./assets/levelcomplete.png").convert()
logo = pygame.image.load("./assets/logo.png").convert_alpha()
fadeout = pygame.image.load("./assets/fadeout2.png")
warpBGHor = pygame.image.load("./assets/warpsHorizontal.png").convert()
warpBGVer = pygame.image.load("./assets/warpsVertical.png").convert()
target = pygame.image.load("./assets/target.png").convert_alpha()

# Pre-render some text since it never changes
subtitle = font.render("Pygame Edition", 1, CYAN)
levelSelect = font.render("Select Stage", 1, CYAN)

def str2bool(v):    # Python can't convert strings to booleans. "Fine I'll do it myself"
  return v.lower() in ("true", "t", "1", "1\n", "true\n")

# levels.vvvvvv is a JSON file which stores the names and folders of each level
with open("levels.vvvvvv", 'r') as levelarray:
    levels = json.loads(levelarray.read())
levelFolder = levels[0]["folder"]

# records.vvvvvv stores your best times and lowest deaths for each level
# I'd encrypt it to avoid cheating but that's a bit too fancy
with open("records.vvvvvv", 'r') as recordArray:
    records = json.loads(recordArray.read())
  

# CLASSES

class Player:
    def __init__(self):
        self.x = 0              # Player X
        self.y = 0              # Player Y
        self.width = 50         # Player width, for collision detection
        self.height = 96        # Player height
        self.speed = 12         # Player X maximum speed
        self.yacceleration = 16  # Player Y maximum speed
        self.acceleration = 0   # Player X current speed
        self.autoAdjust = True  # Autoadjust to align to walls?
        
        self.inputValues = [0,0,1,0,0] # Used for replays / Overhauls self.walking, self.movement, and overall simplifies the code
        # All values are Boolean, 0 = False, 1 = True : 1st value is Left press. 2nd value is Right press. 3rd is flip key. 4th is R key. 5th is frame count
        
        # These values are displayed when completing a level and saved as high scores
        self.deaths = 0
        self.flips = 0
        self.mins = 0
        self.secs = 0
        self.frames = 0
        self.targethits = 0   # Targets broke
        
        self.replay = 0            # Arithmetic logic for saving/playing replays
        self.fullReplay = []
        self.inputs = []
        self.frameinput = []

        self.grounded = False      # Touching the ground? (true = able to flip)
        self.flipped = False       # Currently flipped?
        self.touchedLine = False   # Touched a gravity line? (allows for smoother easing)
        self.facingRight = True    # Facing right? (whether to flip texture or not)
        self.alive = True          # Alive?
        self.hidden = False        # Make the sprite visible?
        self.blocked = [False, False]           # [able to move left, able to move right]
        self.verticalPlatform = [False, False]  # [platform position, platform speed] - Vertical platforms are harrrrd
        self.winTarget = []        # Position to automatically walk to upon touching a teleporter
        self.winLines = []         # Text that's displayed during winning cutscene - only rendered once for the sake of optimizng

        self.animationSpeed = 5    # Speed of walking animation
        self.animationTimer = 0    # ^ timer
        self.coyoteFrames = 5      # Time window where you're STILL allowed to flip, even after leaving the ground
        self.coyoteTimer = 0       # ^ timer
        self.deathStall = 60       # Time to wait before respawning
        self.deathTimer = 0        # ^ timer
        self.winTimer = 0          # How many frames have passed since you beat the level - for timing the win cutscene
        self.textboxBuffer = False # Set to true in ending cutscene to progress to main menu
        self.bufferWindow = 7      # The buffer window for inputting a flip
        self.buffer = -260        # ^ timer (4140     
        self.localTimer = 0        # Timer used for detecting collision
        self.lineTimer = 0         # Timer used for avoiding line collision
        self.flipable = False      # Able to flip directions?
        self.pendingDie = 0        # If over 1, kill the player. Die() adds 1 every frame.
        self.pendDieTemp = 0       # ^ temp
    def refresh(self):
        # Reset these values, calculate them later
        self.grounded = False
        self.blocked = [False, False]
        self.verticalPlatform = [-999, False]  # Assume you're not touching a vertical platform. You're probably not
        self.autoAdjust = True

    def getStandingOn(self, checkFlip=True):
        # Get the X position of the two tiles you're standing on
        playertiles = [math.floor((self.x + 7) / 32), math.floor((self.y + 11) / 32) + 3]
        if self.flipped and checkFlip:
            playertiles[1] = math.floor((self.y - 11) / 32)  # Adjust the math if you're flipped
        return playertiles

    def touching(self, objecttop, forgiveness=0, size=[1, 1], nextframe = False):  # Check if hitbox is touching player
        if nextframe == False:
            playertop = [self.x, self.y]
        else:
            playertop = [self.x + self.acceleration, self.y]
        playerbottom = [playertop[0] + self.width, playertop[1] + self.height]  
        objectbottom = [objecttop[0] + (32 * size[0]), objecttop[1] + (32 * size[1])]
        objecttop[0] += forgiveness    # Forgiveness shrinks the hitbox by the specified amount of pixels
        objectbottom[0] -= forgiveness # ^ it makes spikes and enemies more generous, etc
        objecttop[1] += forgiveness * 1
        objectbottom[1] -= forgiveness * 1
        return collision(playertop, playerbottom, objecttop, objectbottom)

    def turn(self):  # Flip player X
        for num in range(30, 33):
            sprites[num] = pygame.transform.flip(sprites[num], True, False)
        self.facingRight = not self.facingRight

    def flip(self, auto=False):  # Flip player Y
        if not auto:
            self.flips += 1
            if self.flipped:
                sfx_flop.play()
##                self.y -= 8
            else:
##                self.y += 8
                sfx_flip.play()
        for num in range(30, 33):
            sprites[num] = pygame.transform.flip(sprites[num], False, True)
        self.flipped = not self.flipped

    def die(self):  # Kill the player
        global setting
        self.pendDieTemp = 0
        if self.pendingDie >= 1 and not setting.invincible:
            sfx_hurt.play()
            self.acceleration = 0 # Remove all movement before dying
            self.buffer = 0 # Can't flip after death :P
            self.localTimer = 0 # Prevents clipping while respawning
            self.alive = False
            self.deaths += 1
            self.pendingDie = 0
            self.pendDieTemp = 0
        else:
            self.pendingDie += 1
    def getInput(self):
        # print(self.replay)
        if self.winTimer == 0 and self.replay == 0:
            c = self.inputValues.copy()
            if key[pygame.K_LEFT] or key[pygame.K_a] and not (key[pygame.K_RIGHT] or key[pygame.K_d]):
                self.inputValues[0] = 1
            else:
                self.inputValues[0] = 0
            if key[pygame.K_RIGHT] or key[pygame.K_d] and not (key[pygame.K_LEFT] or key[pygame.K_a]):
                self.inputValues[1] = 1
            else:
                self.inputValues[1] = 0          
            if key[pygame.K_SPACE] or key[pygame.K_UP] or key[pygame.K_DOWN] or key[pygame.K_z] or key[pygame.K_w] or key[pygame.K_s] or key[pygame.K_v] or key[pygame.K_RETURN]:
                    self.inputValues[2] = 1
            else:
                    self.inputValues[2] = 0
            if key[pygame.K_r]:
                    self.inputValues[3] = 1
            else:
                    self.inputValues[3] = 0
            if c != self.inputValues:
                self.inputValues[4] = (self.frames + self.secs * 60 + self.mins * 3600)
                self.fullReplay.append(self.inputValues.copy())

        elif self.winTimer == 0 and self.replay >= 1:
            # print(self.frameinput[self.replay - 1])
            if (self.frames + self.secs * 60 + self.mins * 3600) == int(self.frameinput[self.replay - 1]):
                num = int(self.inputs[self.replay - 1],2)
                if num >= 8:
                    self.inputValues[0] = 1
                    num -= 8
                else:
                    self.inputValues[0] = 0
                if num >= 4:
                    self.inputValues[1] = 1
                    num -= 4
                else:
                    self.inputValues[1] = 0
                if num >= 2:
                    self.inputValues[2] = 1
                    num -= 2
                else:
                    self.inputValues[2] = 0
                if num >= 1:
                    self.inputValues[3] = 1
                else:
                    self.inputValues[3] = 0
                self.replay += 1
            elif self.frameinput[self.replay - 1] == 0:
                self.replay = - 1   # Stop the replay once its over. Theoretically doesn't matter but in the case of a desynced replay, gives control back to the player.
        else:
            self.inputValues = [0,0,0,0,(self.frames + self.secs * 60 + self.mins * 3600)]
            if self.winTimer == 1:
                self.fullReplay.append(self.inputValues.copy())
    def nani(self): # Secret
        global checkpointSheet, playerSheet, sfx_save, sfx_hurt
        playerSheet = Spritesheet("./assets/player(S).png")
        checkpointSheet = Spritesheet("./assets/checkpoint(S).png")
        sfx_save = pygame.mixer.Sound("./assets/sounds/hurt.wav")
        sfx_hurt = pygame.mixer.Sound("./assets/sounds/bang.wav")
        setting.updateVolume()
    def exist(self):  # Buckle up, this one's a big boy
        global breakingPlatforms, ingame, savedGame, setting, levelnum
        # Gravity line easing
        if self.touchedLine:
            self.yacceleration -= round(savedVelocity / 4.5)
            self.coyoteTimer = self.coyoteFrames
            self.lineTimer = 1
        elif self.yacceleration < savedVelocity:
            self.yacceleration += round(savedVelocity / 4.5)
            self.coyoteTimer = self.coyoteFrames
        if self.lineTimer >= 6:
            self.lineTimer = 0
        if (self.blocked[0] or self.blocked[1]) and self.yacceleration != savedVelocity and self.lineTimer == 2: # Prevents a bug in which the player gets stuck on a ceiling when using gravity lines
            if self.flipped:
                self.y -= 16
            if not self.flipped:
                self.y += 16
##        if self.velocity != savedVelocity and self.lineTimer > 2 and self.lineTimer < 6:
##            if self.blocked[0] or self.blocked[1]:
##                self.x -= self.acceleration
##                if self.flipped:
##                    self.y += 8
##                if not self.flipped:
##                    self.y -= 8
        if self.lineTimer > 0: # Increments the timer AFTER calculations done above
            self.lineTimer += 1
            
            
        if self.yacceleration <= 1:
            if self.flipped and not self.grounded:
                self.y -= 16
            elif self.flipped:  
                self.y -= 1
            if not self.flipped and not self.grounded: # When you flip on a gravity line, make the transition smoother.
                self.y += 16
            elif self.flipped:  # When walking into a vertical gravity line, slightly shift the player towards the ceiling.
                self.y += 1
            self.flip(True)
            self.touchedLine = False


        if self.alive:  # If you're alive...
            if self.pendingDie >= 0:
                self.pendDieTemp += 1
                if self.pendingDie > 0 and self.pendDieTemp >= 4:
                    self.pendingDie = 0
                    self.pendDieTemp = 0
            if (self.grounded or self.coyoteTimer < self.coyoteFrames) and self.buffer >= 0 and self.buffer < self.bufferWindow and self.yacceleration == savedVelocity:
                self.flipable = True
            else:
                self.flipable = False

                # localTimer used for misc. variables. Used in gameplay for flipping off of targets.
            if self.localTimer > 0:
                if self.winTimer == 0:
                    self.localTimer -= 1
                    self.flipable = True
                
            if (self.blocked[0] and self.blocked[1]) or self.coyoteTimer == 1:
                self.autoAdjust = False
                
            if self.verticalPlatform[0] != -999:  # If you ARE on a vertical platform
                self.grounded = True  # Consider the player grounded
                self.flipable = True
                self.coyoteTimer = 0
                if self.flipped:  # If flipped
                    if self.y - self.verticalPlatform[0] >= 16 and self.y - self.verticalPlatform[0] <= 48:
                        self.y = self.verticalPlatform[0] + 32  # SET the player Y position to below the platform
                    #if not self.verticalPlatform[1]:
                        #self.y -= 12  # If moving up, tweak the position a little
                else:  # If not flipped
                    if self.y - self.verticalPlatform[0] >= -112 and self.y - self.verticalPlatform[0] <= -80:
                        self.y = self.verticalPlatform[0] - self.height  # SET the player Y position to above the platform
                    #if self.verticalPlatform[1]:
                        #self.y += 3  # If moving down, tweak the position a little
                        

            elif not self.grounded:  # If the player is STILL not grounded...
                self.coyoteTimer += 1  # Start coyote timer, which allows flipping for a few frames after leaving the ground
                
                if self.flipped:
                    if self.coyoteTimer > 0 and self.coyoteTimer < 5 and self.yacceleration == savedVelocity:
                        self.y += (16 - round((self.coyoteTimer / self.coyoteFrames) * 16))
                    self.y -= self.yacceleration  # Fall up!
                else:
                    if self.coyoteTimer > 0 and self.coyoteTimer < 5 and self.yacceleration == savedVelocity:
                        self.y -= (16 - round((self.coyoteTimer / self.coyoteFrames) * 16))
                    self.y += self.yacceleration  # Fall down!
                        
            elif self.verticalPlatform[0] == -999:  # If you're NOT touching a vertical platform
                if self.y % 32 != 0:
                    self.autoAdjust = False
                if self.autoAdjust == False:
                    self.x += self.acceleration / 1.2
                if self.flipped:
                    self.y = math.ceil((self.y - 10) / 32) * 32  # Round Y position to nearest 32 if grounded
                else:
                    self.y = math.floor((self.y + 10) / 32) * 32
                                            
            if self.blocked[1] and self.yacceleration == savedVelocity and self.autoAdjust == True:
                if self.acceleration >= 9:
                    self.x = math.ceil(self.x / 32) * 32 - 12
                elif self.acceleration >= 0 and round(self.x / 32) * 32 - 20 < self.x:
                     self.x = math.ceil(self.x / 32) * 32 - 12
            if self.blocked[0] and self.yacceleration == savedVelocity and self.autoAdjust == True:
                if self.acceleration <= 9:
                    self.x = round(self.x / 32) * 32 - 4
                elif self.acceleration <= 0 and round(self.x / 32) * 32 - 4 > self.x:
                    self.x = round(self.x / 32) * 32 - 4   
                        
            if self.winTimer > 0 and self.winTimer < 160:
                self.acceleration = 0
                # If you touched a teleporter, pathfind to winTarget (center of the teleporter)
                if self.winTarget[1] and self.x < self.winTarget[0] and not self.blocked[1]:
                    self.x += self.speed
                    self.inputValues[1] = 1
                    self.animationTimer += 1
                elif not self.winTarget[1] and self.x > self.winTarget[0] and not self.blocked[0]:
                    self.x -= self.speed
                    self.inputValues[0] = 1
                    self.animationTimer += 1
                else:
                    self.inputValues[0] = 0
                    self.inputValues[1] = 0
            elif self.inputValues[1] == 1:  # If a "right" key is pressed or held
                if not self.blocked[1]:
                    if self.acceleration <= self.speed:
                        self.acceleration += 2.2
                    if self.acceleration < -6:
                        self.acceleration += 5.3
                    if self.acceleration > self.speed:
                        self.acceleration = self.speed
                    if self.blocked[0]:
                        self.x += 2.2
                    self.x += self.acceleration  # Move right if you're able to
                    self.animationTimer += 1
            elif self.inputValues[0] == 1:  # If a "left" key is pressed or held
                if not self.blocked[0]:
                    if self.acceleration >= -self.speed:
                        self.acceleration -= 2.2
                    if self.acceleration > 6:
                        self.acceleration -= 5.3
                    if self.acceleration < -self.speed:
                        self.acceleration = -self.speed
                    if self.blocked[1]:
                        self.x -= 2.2
                    self.x += self.acceleration  # Move left if you're able to
                    self.animationTimer += 1
            else:
                self.acceleration = round(self.acceleration / 1.5)
                if self.blocked[0] and self.blocked[1]:
                    self.acceleration = self.acceleration * 1.5
                if self.blocked[0] or self.blocked[1]:
                    self.acceleration = 0
                if self.acceleration <= 1 and self.acceleration >= -1:
                    self.acceleration = 0
                self.x += self.acceleration

                 
            self.x = round(self.x)      # Finally, end the collision detection calculation and add deltaX and deltaY to the player.
            
            if self.inputValues[0] == 0 and self.inputValues[1] == 0:
                self.animationTimer = self.animationSpeed - 1  # Change to 'walking' sprite as soon as you start moving again
            if self.inputValues[2] == 1:
                self.buffer += 1
                if self.buffer == -2:
                    sfx_secret.play()
                    self.nani()
            else:
                self.buffer = 0
                
            if self.inputValues[2] == 1 and self.yacceleration == savedVelocity and self.buffer < self.bufferWindow and self.buffer > 0:
                if self.flipable or setting.flippyboi:
                    self.flip()
                    self.localTimer = 0
                    self.coyoteTimer = self.coyoteFrames
                    self.flipable = False
                    self.buffer = 69
            if self.inputValues[3] == 1:
                if setting.invincible:
                    temp = True
                    setting.invincible = False
                else:
                    temp = False
                self.die()  # Die if you press R
                self.die()
                setting.invincible = temp    
            for event in events:
                if event.type == pygame.KEYDOWN and self.winTimer == 0:
                    
                    if event.key == pygame.K_COMMA and setting.debugtools == True:  # Debug, moves player 1 pixel at a time
                        self.x -= 1
                    if event.key == pygame.K_PERIOD and setting.debugtools == True:
                        self.x += 1

            if not player.hidden and key[pygame.K_c] and key[pygame.K_h] and mouse[0] and setting.debugtools == True:   # Not a cheat
                self.x, self.y = pygame.mouse.get_pos()   # Not a cheat
                self.x -= 30   # Not a cheat
                self.y -= 50   # Not a cheat
                
            if self.targethits >= 10 and self.winTimer < 1:
                self.winTimer = 190
                
            if (self.inputValues[0] == 1 and self.facingRight) or (self.inputValues[1] == 1 and not self.facingRight):
                self.turn()  # Flip player X when necessary

            if self.y < -32:  # Top exit
                if room.meta["warp"] < 2 or player.flipped:
                    newroom([0, 1], [self.x, screenSize[1] - 16], 2)
            if self.y > screenSize[1] - 16:  # Bottom Exit
                if room.meta["warp"] < 2 or not player.flipped:
                    newroom([0, -1], [self.x, -32], 2)
            if self.x < -32:  # Left Exit
                newroom([-1, 0], [screenSize[0] - 16 + self.acceleration, self.y], 1)
            if self.x > screenSize[0] - 16:  # Right Exit
                newroom([1, 0], [-32 + self.acceleration, self.y], 1)

        else:  # If dead
            self.deathTimer += 1 # Increase death timer
            if self.deathTimer % 8 < 6 and self.deathTimer < 45:
                self.hidden = False # Adds flashing to the death animation
            else:
                self.hidden = True
            if self.deathTimer >= self.deathStall:  # After you were dead for a little while...
                self.deathTimer = 0
                self.hidden = False
                oldX, oldY = [room.x, room.y]
                room.x, room.y, self.x, self.y, spawnFlipped = checkpoint  # Respawn at checkpoint
                self.x = (math.floor(self.x / 8) * 8) + 10  # Round X position a little
                if [oldX, oldY] != [room.x, room.y]:
                    loadroom(room.x, room.y)    # If checkpoint was in a different room, load it

                self.alive = True  # He lives!
                breakingPlatforms = {}  # Clear breaking platform animations
                if not self.facingRight:
                    self.turn()  # Change direction if necessary
                if (spawnFlipped and not self.flipped) or (not spawnFlipped and self.flipped):
                    self.flip(True)  # Flip if necessary

        if self.winTimer > 0:   # Win cutscene
            self.winTimer += 1
            if self.winTimer < 80:
                pygame.mixer.music.set_volume(setting.musicvolume / 80 * (80 - self.winTimer))
            if self.winTimer > 80 and self.winTimer < 330:
                pygame.mixer.music.stop()
            if self.winTimer in [70, 130, 161 , 192]:
                flash(8)    # Flash screen four times...
                if self.targethits >= 10:
                    sfx_success.play()
                else:
                    sfx_bang.play()
            if self.winTimer == 235:
                self.hidden = True      # ...then hide the player...
                pygame.mixer.music.set_volume(setting.musicvolume)
                sfx_tele.play()
            if self.winTimer == 335:
                self.hidden = True      # ... again, just to be safe.
                pygame.mixer.music.load("./assets/musicpack" + str(setting.musicpackSelected) + "/fanfare.ogg")  # ...then play a little jingle...
                pygame.mixer.music.play(1)
                localreplaylist = []
                for file in os.listdir("replays"):
                    
                    if file.endswith(".replay"):
                        localreplaylist.append(file)

                self.localTimer = len(localreplaylist)
                    
            if self.winTimer > 335 and self.textboxBuffer == False:
                screen.blit(levelComplete, (288, 50))   # ...then display "level complete"...
                if self.localTimer < 10:
                    replaytext = medfont.render("Press ENTER to save a replay!", 1, WHITE)
                else:
                    replaytext = medfont.render('', 1, WHITE)
                screen.blit(replaytext, (20, screenSize[1] - 35))
                for event in events:
                    if key[pygame.K_RETURN]:
                        # Checks to see if you have 9 or less replays, if so, add it.
                        
                        if self.replay == 0 and self.localTimer < 10:
                            self.localTimer = 100
                            self.replay = -1
                            now = datetime.now()
                            current_time = './replays/' + str(now.strftime("%D")).replace('/','-') + ' ' + now.strftime("%H;%M") + ".replay"
                            with open(current_time, 'w') as s:
                                s.write(str(levelnum) + '\n' + str(setting.debugtools) + '\n' + str(setting.invincible) + '\n' + str(setting.flippyboi) + '\n')
                                x = 0
                                line = ''
                                while x < len(self.fullReplay):
                                    y = 0
                                    while y < len(self.fullReplay[x]):
                                        s.write(str(self.fullReplay[x][y]))
                                        y += 1
                                    s.write('\n')
                                    x += 1
                if setting.invincible or setting.flippyboi or setting.debugtools:
                    messages = [
                        "You've cheated " + area,
                        "Flips: " + str(player.flips),
                        "Deaths: " + str(player.deaths),
                        "Time: " + str(player.mins) + ":" + str(player.secs).zfill(2) + "." + str(round(player.frames / 60 * 100)).zfill(2),
                        "Congratulations?",
                        "Press ACTION to continue"
                    ]
                else:
                    messages = [    # These messages will display one by one
                        "You've completed " + area,
                        "Flips: " + str(player.flips),
                        "Deaths: " + str(player.deaths),
                        "Time: " + str(player.mins) + ":" + str(player.secs).zfill(2) + "." + str(round(player.frames / 60 * 100)).zfill(2),
                        "Congratulations!",
                        "Press ACTION to continue"
                    ]
                    

                if not len(self.winLines):
                    for i in range(len(messages)):  # Render win lines, but only once
                        msg = bigfont.render(messages[i], 1, WHITE)  # Render
                        msgPos = (screenSize[0] / 2) - (msg.get_width() / 2)  # Center
                        self.winLines.append([msg, msgPos])  # Save
            # Display the messages in the array above, line by line            
            if self.winTimer > 335 and self.textboxBuffer == False: screen.blit(self.winLines[0][0], (self.winLines[0][1], 300))
            if self.winTimer > 410 and self.textboxBuffer == False: screen.blit(self.winLines[1][0], (self.winLines[1][1], 450))
            if self.winTimer > 455 and self.textboxBuffer == False: screen.blit(self.winLines[2][0], (self.winLines[2][1], 530))
            if self.winTimer > 500 and self.textboxBuffer == False: screen.blit(self.winLines[3][0], (self.winLines[3][1], 610))
            if self.winTimer > 565 and self.textboxBuffer == False: screen.blit(self.winLines[4][0], (self.winLines[4][1], 690))
            if self.winTimer > 690 and self.textboxBuffer == False: 
                screen.blit(self.winLines[5][0], (self.winLines[5][1], 770))
                for event in events:
                    if event.type == pygame.KEYDOWN and event.key in flipKeys and self.winTimer > 695:  # When you press SPACE (or any flip key) to quit to menu
                        self.textboxBuffer = True                               # Will wait 1 second after this textbox appears for winTimer to stop.
                                                                                # If pressed, continue the timer.
                        postedRecord = False
                        if setting.invincible == False and setting.flippyboi == False and setting.debugtools == False:
                            record = [levelFolder, [player.mins, player.secs, player.frames], player.deaths]    # Store time and deaths
                            for r in range(len(records)):
                                if records[r][0] == levelFolder:    # If a previous record exists, compare the new one and check for improvements
                                    oldTime = (records[r][1][0] * 60) + records[r][1][1] + (records[r][1][2] / 60)
                                    newTime = (record[1][0] * 60) + record[1][1] + (record[1][2] / 60)
                                    if oldTime < newTime: record[1] = records[r][1]     # If this run's time was lower, replace record
                                    if records[r][2] < player.deaths: record[2] = records[r][2]     # If this run's death count was lower, replace record
                                    records[r] = record    # Store record
                                    postedRecord = True
                            if not postedRecord:
                                records.append(record)  # If no previous record exists, store this run as the record
                            with open("records.vvvvvv", 'w') as data: json.dump(records, data)  # Save to record file

                        
            if self.winTimer > 760 and self.textboxBuffer == False: #Freezes the timer until the ACTION key is pressed
                        self.winTimer = 760            
            if self.winTimer > 760 and self.winTimer < 815: screen.blit(fadeout, (-1970 + ((self.winTimer - 760) * 36), 0)) #Move the fadeout image across the screen
            if self.winTimer >= 815:
                # Saves a replay of the level. Hopefully it will take 5 frames or less to complete, otherwise the game will lag.
                # Due to the size of the file, it should hopefully be fairly quick since the file size is pretty small
                screen.blit(fadeout, (0, 0))

               
            if self.winTimer > 820:
                        # Quit level, delete save, display menu
                        ingame = False
                        sfx_save.play()
                        getMusic("menu")
                        savedGame = False
                        try: os.remove('save.vvvvvv')    # Delete save file
                        except FileNotFoundError: pass   # Do nothing if there never was a save file
                        self.frames = 0
                        self.secs = 0
                        self.mins = 0
                        buildmenu()

        # Basic timer
        else:
            self.frames += 1
            if self.frames >= 60:   # Every 60 frames, add 1 second
                self.frames = 0
                self.secs += 1
                if self.secs >= 60:     # Every 60 seconds, add 1 minute
                    self.secs = 0
                    self.mins += 1

        spriteNumber = 30  # Idle
        if not self.alive:
            spriteNumber = 32  # Dead
        elif self.animationTimer > self.animationSpeed * 2:
            self.animationTimer = 0  # Timer for walking animation
        elif self.animationTimer > self.animationSpeed and self.blocked == [False,False]:
            spriteNumber = 31  # Walking

        if not self.hidden:
            screen.blit(sprites[spriteNumber], (self.x, self.y))  # Render player

        if room.meta["warp"] == 1:  # If warping is enabled, render a second player if they're touching a screen border
            if self.x < 33 and not self.hidden:
                screen.blit(sprites[spriteNumber], (self.x + screenSize[0] + 18, self.y))
            elif self.x > screenSize[0] - 33 and not self.hidden:
                screen.blit(sprites[spriteNumber], (self.x - screenSize[0] - 18, self.y))

        if room.meta["warp"] == 2:  # Same as above but for vertical warping
            if self.y < 96 and not self.hidden:
                screen.blit(sprites[spriteNumber], (self.x, self.y + (screenSize[1] + 0)))
                if self.alive and self.yacceleration == 16 and not self.grounded and self.flipped:
                    self.y -= 4
            elif self.y > screenSize[1] - 96 and not self.hidden:
                screen.blit(sprites[spriteNumber], (self.x, self.y - screenSize[1] - 32))
                if self.alive and self.yacceleration == 16 and not self.grounded and not self.flipped:
                    self.y += 8

class Room:
    def __init__(self, x=5, y=5):
        global bgCol, breakingPlatforms, warpBGs, roomLoadTime
        self.x = x              # X position of room
        self.y = y              # Y position of room
        self.tiles = {}         # Object containing all tiles in the room
        self.platforms = []     # Array of all moving platforms in the room
        self.enemies = []       # Array of all enemies in the room
        self.lines = []         # Array of all the gravity lines in the room
        self.meta = {"name": "Outer Space", "color": 0, "tileset": 7, "warp": 0, "enemyType": [1, 1, 1]}    # Metadata
        self.exists = True
        self.platformException = False
        
        starttime = round(time.time() * 1000)  # Begin room load stopwatch (debug)
        
        try:  # Attempt to open the room file
            with open("./" + levelFolder + "/" + str(self.x) + "," + str(self.y) + '.vvvvvv', 'r') as lvl:
                level = json.loads(lvl.read())
                self.tiles = level["tiles"]
                self.platforms = level["platforms"]
                self.enemies = level["enemies"]
                try:
                    self.targets = level["targets"]
                except:
                    self.targets = []
                self.lines = level["lines"]
                self.meta = level["meta"]
        except FileNotFoundError:
            self.exists = False   # Use an empty room if no room file exists

        tileset = 0  # Since the palette is split into different tilesets, fetch the correct one
        if self.meta["tileset"] == 8:
            tileset = 1  # Lab

        elif self.meta["tileset"] == 7:
            tileset = 2  # Warp Zone
        warpBGs = []
        if self.meta["warp"] != 0:
            warpBGs.append(warpBGVer)
            warpBGs.append(warpBGHor) 
        switchtileset(self.meta["tileset"])  # Switch tileset
        
        for i in range(len(sprites)):
            if i <= 29 or (37 <= i <= 49):
                self.recolor(sprites[i], self.meta["color"], tileset)  # Recolor (most) sprites to selected color
        for e in enemySprites:
            for f in e:
                for g in f:
                    self.recolor(g, self.meta["color"], tileset)  # Recolor enemies
        for w in warpBGs:
            self.recolor(w, self.meta["color"], tileset)  # Recolor warp background
        if self.meta["tileset"] == 8:  # Lab tileset
            bgCol = palette[self.meta["color"]][1][8]  # Recolor lab background
        else:
            bgCol = (0, 0, 0, 0)



        for num in range(30, 33):  # Flip player sprites if necessary
            sprites[num] = pygame.transform.flip(sprites[num], not player.facingRight, player.flipped)

        breakingPlatforms = {}  # Reset breaking platforms

        roomLoadTime = round(time.time() * 1000) - starttime  # Finish room load stopwatch (milliseconds)
        
    def loadEnemies(self):
        # Prepare Enemy and Platform classes
        for i in range(len(self.enemies)): self.enemies[i] = Enemy(self.enemies[i])
        for i in range(len(self.platforms)): self.platforms[i] = Platform(self.platforms[i])
        try:
            for i in range(len(self.targets)): self.targets[i] = Target(self.targets[i])
        except:
            dont = 'fucking bother'


    def recolor(self, obj, color, tileset):  # Recolors a sprite using palette.png
        pixels = pygame.PixelArray(obj)  # Get the color of each pixel

        for (x, col) in enumerate(palette[0][tileset]):  # For each GREY color in the palette (top row)
            newcol = palette[color][tileset][x]  # Choose the new palette row (color)
            pixels.replace((col[1], col[2], col[3]), (newcol[1], newcol[2], newcol[3]))  # Replace grey with color


    def renderBG(self):
        global warpBGPos
        screen.fill((bgCol[1], bgCol[2], bgCol[3]))  # Set background color (black in all tilesets except lab)

        if self.meta["warp"]:  # If warping is enabled
            if self.meta["warp"] == 1:
                screen.blit(warpBGs[0], (0 - warpBGPos + 16, 0))  # Render horizontal warp background
            elif self.meta["warp"] == 2:
                screen.blit(warpBGs[1], (0, 0 - warpBGPos))  # Render vertical warp background
            warpBGPos += warpBGSpeed
            if warpBGPos >= 96:  # Loop background by secretly shifting it back
                warpBGPos = 0

        elif self.meta["tileset"] <= 6:  # If space station tileset is used
            for (st, s) in enumerate(stars):  # Render stars in the background
                rect(screen, grey(255 - (s[2] * 5)), (s[0], s[1], 5, 5), 0)
                s[0] -= starSpeed - round(s[2] / 5)   # Move stars left
                if s[0] < 0:  # Delete stars that are off screen so the array doesn't clutter up
                    del stars[st]

        elif self.meta["tileset"] == 7:  # If warp zone tileset is used
            for (st, s) in enumerate(stars):  # Also render stars
                rect(screen, grey(255 - (s[2] * 5)), (s[0], s[1], 5, 5), 0)
                s[1] -= starSpeed - round(s[2] / 5)   # Move stars up
                if s[1] < 0:  # Delete stars that are off screen so the array doesn't clutter up
                    del stars[st]

        else:  # If you *are* using the lab tileset
            for (st, s) in enumerate(rects):  # Render rectangles in the background
                rectType = s[2]
                rectcol = palette[self.meta["color"]][1][6]  # Color rectangles
                rectcol = (rectcol[1], rectcol[2], rectcol[3])
                step = 1
                if not rectType % 2:
                    step *= -1  # If rectType is even, reverse direction
                if rectType <= 2:  # Horizontal rectanges
                    rect(screen, rectcol, (s[0], s[1], 128, 40), 3)  # Render
                    s[0] -= (starSpeed + 4) * step  # Move left/right
                    if s[0] < -50 or s[0] > screenSize[0] + 50:  # Delete if off screen
                        del rects[st]
                elif rectType >= 3:
                    rect(screen, rectcol, (s[0], s[1], 40, 128), 3)  # Render
                    s[1] -= (starSpeed + 4) * step  # Move up/down
                    if s[1] < - 50 or s[1] > screenSize[1] + 20:  # Delete if off screen
                        del rects[st]


    def checkLines(self):

        for (i, l) in enumerate(self.lines):    # For each gravity line
            lineSize = [0, 0]
            linePos = [l[0], l[1]]
            lineCol = 255
            if l[3]:  # Vertical
                lineSize[1] = l[2]
                linePos[0] -= 3
            else:  # Horizontal
                lineSize[0] = l[2]
                linePos[1] += 1
            if l[4] > 0: lineCol = 180
            if player.alive and player.lineTimer == 0 and player.yacceleration == savedVelocity and \
                    collision([player.x, player.y], [player.x + (player.width - 2), player.y + player.height],
                    [l[0], l[1]], [l[0] + lineSize[0], l[1] + lineSize[1]]):
                if not l[4]:    # If gravity line is touched and not on cooldown
                    sfx_blip.play()
                    player.touchedLine = True   # Flip gravity, ease the player's velocity a bit
                    l[4] = lineCooldown
                    if l[3]:
                        l[4] = lineCooldown - 2
            elif l[4] > 0:  # Decrease line cooldown, only when not touching it
                l[4] -= 1
            line(screen, grey(lineCol), (linePos[0], linePos[1]), (linePos[0] + lineSize[0], linePos[1] + lineSize[1]), lineWidth)
            self.lines[i] = l


    def run(self):
        if globalTimer > 1 and globalTimer < 3 + self.meta["warp"]:
            # print('hey')
            reparseSpritesheets(globalTimer - 2)
        for z in range(3):
            for i in self.tiles:  # For each object in the screen...
                tileX, tileY, tileZ = parsecoords(i)
                if tileZ == z:  # Layer objects correctly (blocks < spikes < entities)

                    spriteNum = self.tiles[i]
                    if spriteNum == 33 or spriteNum == 35:  # Checkpoints
                        offset = -32
                        saveflipped = False
                        if spriteNum == 35:  # Flipped checkpoint
                            offset = 0
                            saveflipped = True
                        if checkpoint == [self.x, self.y, tileX * 32, (tileY * 32) + offset, saveflipped]:
                            spriteNum += 1  # Change texture if checkpoint is activated
                        elif player.touching([tileX * 32, tileY * 32], 8, [2, 2]):
                            setcheckpoint(tileX * 32, (tileY * 32) + offset,
                                          saveflipped)  # Set checkpoint if not activated

                                
                    if 26 <= spriteNum <= 29 and player.alive:  # If object is a spike
                        if player.touching([tileX * 32, tileY * 32], 10):
                                player.die()# If you touch a spike, die!
                                player.pendingDie -= 0.4
                                if (player.grounded or player.flipable) and self.platformException == False:
                                    player.die()
                                    player.die()
                            
                    if player.alive and issolid(spriteNum):  # If object is a solid block
                        
                        if 37 <= spriteNum <= 40:  # Resize hitbox if object is a breaking platform
                            if not i in breakingPlatforms:  # If not considered 'breaking' yet
                                if solidblock(4, tileX * 32 + 5, tileY * 32):
                                    if spriteNum == 37:  # Break
                                        sfx_beep.play()
                                        breakingPlatforms[i] = 0  # Set animation timer for this platform
                            elif breakingPlatforms[i] < breakSpeed * 3:
                                solidblock(4, tileX * 32 + 5, tileY * 32)

                        elif solidblock(1, tileX * 32, tileY * 32):  # Ground/block player if touching a solid block
                            if 42 <= spriteNum <= 45:  # If tile is a left moving conveyor
                                if not player.blocked[0]:  # Move left if not blocked
                                    if not (player.blocked[1] and player.acceleration > 9): #If wall to the right and holding right, conveyor doesn't move left
                                        player.x -= conveyorSpeed
                                        if player.x % 16 == 0 and player.acceleration < -9:
                                            player.x += 3
                                        player.acceleration -= (conveyorSpeed / 1024)         # Fixes bug that prevents player from moving on conveyor if next to a wall
                            if 46 <= spriteNum <= 49:  # If tile is a right moving conveyor
                                if not player.blocked[1]:  # Move right if not blocked
                                    if not (player.blocked[0] and player.acceleration < -9): #If wall to the left and holding left, conveyor doesn't move right
                                        player.x += conveyorSpeed
                                        if player.x % 16 == 0 and player.acceleration > 9:
                                            player.x -= 3
                                        player.acceleration += (conveyorSpeed / 1024)        # Fixes bug that prevents player from moving on conveyor if next to a wall

                    if i in breakingPlatforms:  # Render breaking platforms
                        if player.alive: breakingPlatforms[i] += 1
                        breakState = breakingPlatforms[i]
                        spriteNum = 38
                        # Change texture depending on how broken the platform is
                        if breakState > breakSpeed * 3:
                            spriteNum = 41
                        elif breakState > breakSpeed * 2:
                            spriteNum = 40
                        elif breakState > breakSpeed:
                            spriteNum = 39

                    if spriteNum == 42 or spriteNum == 46:  # Animate coveyors
                        spriteNum += math.floor(globalTimer % (conveyorAnimation*4) / conveyorAnimation)

                    if spriteNum == 52:  # Teleporter
                        if player.touching([tileX * 32, tileY * 32], 40, [12, 12]) and player.winTimer == 0:
                            player.winTimer += 1    # Win the game!
                            player.winTarget = [tileX * 32 + 176, (tileX * 32 + 176) > player.x]  # Where to walk to?
                            sfx_boop.play()
                        elif player.winTimer > 0 and not player.hidden:
                            spriteNum += math.ceil((player.winTimer / 4) % 4)   # Animate teleporter

                    if self.tiles[i] != 50 and self.tiles[i] != 51:  # Unless the object should be invisible (boundries, etc)
                        screen.blit(sprites[spriteNum], (tileX * 32, tileY * 32))  # Render the object

        for enemy in self.enemies: enemy.move()             # Move enemies
        for platform in self.platforms: platform.move()     # Move platforms
        try:
            for target in self.targets: target.move()
        except AttributeError:
            dont = 'fucking bother'
            


    def renderName(self, font, screenSize, screen):
        if len(self.meta["name"]) and player.winTimer == 0:
            roomname = font.render(self.meta["name"], 1, WHITE)  # Render room name
            roomnamex = (screenSize[0] / 2) - (roomname.get_width() / 2)  # Center the room name
            if len(self.meta["name"]):
                rect(screen, BLACK, (0, screenSize[1] - 32, screenSize[0], 32))
                screen.blit(roomname, (roomnamex, screenSize[1] - 28))  # Render room nome


class Enemy:
    def __init__(self, arr):
        self.x, self.y, self.xSpeed, self.ySpeed, self.type = arr
        self.size = 2 * (arr[4]+1)
        self.hitbox = 11
        self.sprite = room.meta["enemyType"][self.type]

        if self.size == 4:
            self.hitbox = largeHitboxes[self.sprite]   # Make special exceptions for 4x4 enemies

    def move(self):
        global globalTimer
        if player.alive:   # Move enemy (if alive) and round position a little for proper sync
            if self.xSpeed: self.x = roundto(self.x + self.xSpeed, self.xSpeed)
            if self.ySpeed: self.y = roundto(self.y + self.ySpeed, self.ySpeed)

            if player.touching([self.x, self.y], self.hitbox, [self.size, self.size]):
                player.die()  # Die if you're touching the enemy

        animation = math.floor(globalTimer % (enemyAnimation*4) / enemyAnimation)

        wall = switchdirection([self.x, self.y, self.xSpeed, self.ySpeed], self.size, self.size)
        if wall[0]: self.xSpeed *= -1   # Switch direction if wall touched
        if wall[1]: self.ySpeed *= -1

        enemySprite = enemySprites[self.type][self.sprite][animation]
        
        screen.blit(enemySprite, (self.x, self.y))  # Render the enemy

        if room.meta["warp"] == 1:  # Wrap around and render second sprite if warping is enabled and screen border is touched
            if self.x < 60:
                screen.blit(enemySprite, (self.x + screenSize[0], self.y))
            elif self.x > screenSize[0] - 60:
                screen.blit(enemySprite, (self.x - screenSize[0], self.y))
            if self.x < 0:
                self.x = screenSize[0]
            elif self.x > screenSize[0]:
                self.x = 0

        if room.meta["warp"] == 2:  # Same as above but for vertical warping
            if self.y < 60:
                screen.blit(enemySprite, (self.x, self.y + screenSize[1]))
            elif self.y > screenSize[1] - 60:
                screen.blit(enemySprite, (self.x, self.y - screenSize[1]))
            if self.y < 0:
                self.y = screenSize[1]
            elif self.y > screenSize[1]:
                self.y = 0

class Target:
    def __init__(self, arr):
        self.x, self.y, self.xSpeed, self.ySpeed, self.type = arr
        self.size = 2
        self.hitbox = 14
        self.tangible = True

    def move(self):
        global globalTimer
        if player.alive:   # Move enemy (if alive) and round position a little for proper sync
            if self.xSpeed: self.x = roundto(self.x + self.xSpeed, self.xSpeed)
            if self.ySpeed: self.y = roundto(self.y + self.ySpeed, self.ySpeed)

            if player.touching([self.x, self.y], self.hitbox, [self.size, self.size]) and self.tangible:
                sfx_target.play()
                player.targethits += 1
                player.flipable = True  # Break the target, allow the player to flip.
                player.localTimer = 8
                self.tangible = False

                
        wall = switchdirection([self.x, self.y, self.xSpeed, self.ySpeed], self.size, self.size)
        if wall[0]: self.xSpeed *= -1   # Switch direction if wall touched
        if wall[1]: self.ySpeed *= -1
        if self.tangible:
            screen.blit(target, (self.x, self.y))  # Render the enemy

        if room.meta["warp"] == 1:  # Wrap around and render second sprite if warping is enabled and screen border is touched
            if self.x < 60:
                screen.blit(target, (self.x + screenSize[0], self.y))
            elif self.x > screenSize[0] - 60:
                screen.blit(target, (self.x - screenSize[0], self.y))
            if self.x < 0:
                self.x = screenSize[0]
            elif self.x > screenSize[0]:
                self.x = 0

        elif room.meta["warp"] == 2:  # Same as above but for vertical warping
            if self.y < 60:
                screen.blit(target, (self.x, self.y + screenSize[1]))
            elif self.y > screenSize[1] - 60:
                screen.blit(target, (self.x, self.y - screenSize[1]))
            if self.y < 0:
                self.y = screenSize[1]
            elif self.y > screenSize[1]:
                self.y = 0


class Platform:
    def __init__(self, arr):
        self.x, self.y, self.xSpeed, self.ySpeed = arr

    def move(self):
        if player.alive:   # Move platform (if alive) and round position a little for proper sync
            if self.xSpeed: self.x = roundto(self.x + self.xSpeed, self.xSpeed)
            if self.ySpeed: self.y = roundto(self.y + self.ySpeed, self.ySpeed)

        wall = switchdirection([self.x, self.y, self.xSpeed, self.ySpeed], 4, 1, True)
        if wall[0]: self.xSpeed *= -1   # Switch direction if wall or spike touched
        if wall[1]: self.ySpeed *= -1

        # HORIZONTAL PLATFORMS (easy)
        if self.ySpeed == 0 and solidblock(4, self.x + ((player.x - self.x - 24) / 8), self.y):  # Move player with the platform
            if self.xSpeed < 0 and not player.blocked[0] or self.xSpeed > 0 and not player.blocked[1]:  # If left/right is not blocked...
##                if not (player.acceleration < -4 and player.blocked[0]) or not (player.acceleration > 4 and player.blocked[1]):
                if (player.acceleration > -9 and not player.blocked[0]) or (player.acceleration < 9 and not player.blocked[1]):
                    if player.alive:
##                        if player.x + 32 < self.x:
##                            player.x = self.x - 20
##                        elif player.x > self.x + 120:
##                            player.x = self.x + 132
                        
                        player.x += self.xSpeed # Move with the platform
                        if player.acceleration == 0:
                            player.blocked[0] = False
                            player.blocked[1] = False
                    

        # VERTICAL PLATFORMS (hard!!)
        elif self.xSpeed == 0:
            flipoffset = 16  # Offset to apply if flipped/not flipped
            if player.flipped:
                flipoffset = 75
            if (player.alive and not player.flipped and player.touching([self.x, self.y - 16], 0, [4, 1])) or (
                    player.flipped and player.touching([self.x, self.y + 16], -5, [4, 1])):
                if player.x + 40 < self.x:
                    player.blocked[1] = True  # Block right if touching left of platform
                elif player.x > self.x + 120:
                    player.blocked[0] = True  # Block left if touching right of platform
                else:
                    player.verticalPlatform[0] = self.y  # Save Y position of platform for player.exist()
                    player.verticalPlatform[1] = self.ySpeed > 0  # Save direction of platform for player.exist()

        screen.blit(sprites[37], (self.x, self.y))  # Render the platform


class Menu:
    def __init__(self, name, options, yPos=0, bg=True):
        self.name = name
        self.options = options
        self.showBG = bg
        self.selected = 0
        self.locked = []
        self.offset = [30, 45]
        self.pos = [0, yPos*-1]

        # Render each line of text to find the width of the longest one, so that it can be centered
        # Also add up the total heights
        for i in range(len(self.options)):
            option = font.render((self.options[i]).lower(), 1, WHITE)
            width = option.get_width() + (self.offset[0] *i)
            self.pos[1] += option.get_height()
            if width > self.pos[0]:
                self.pos[0] = width
        self.pos[0] = (screenSize[0] / 2) - (self.pos[0] / 2)
        self.pos[1] = (screenSize[1] / 2) - (self.pos[1] / 2) - self.offset[1]

    def run(self):
        global menuBGPos
        count = len(self.options)
        choice = 999    # Placeholder high number because Python thinks (0 == False)

        for event in events:
            if event.type == pygame.KEYDOWN and len(self.options):
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.selected -= 1  # Change selected option when pressing up
                    sfx_menu.play()
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.selected += 1  # Change selected option when pressing down
                    sfx_menu.play()
                elif event.key in flipKeys:   # Select option when pressing space or similar
                    choice = self.selected
                if self.selected >= count:
                    self.selected = 0   # Loop menu around
                elif self.selected < 0:
                    self.selected = count-1
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key in flipKeys:
                    choice = 0  # Unused, but allows support for clicking on empty menus

        if self.showBG:
            screen.blit(menuBG, (0, 0 - menuBGPos))  # Render menu background
            menuBGPos += menuBGSpeed
            if menuBGPos >= 4600:  # Loop background by secretly shifting it back
                menuBGPos = 0
        else:
            screen.fill(BLACK)

        for i in range(count):  # For each option in the menu...
            text = self.options[i]
            col = WHITE

            if i in self.locked:
                col = grey(150)     # Grey out any 'locked' options

            if i == self.selected:
                text = "[ " + text.upper() + " ]"   # Surround option in square brackets if selected
            else:
                text = text.lower()
            option = font.render(text, 1, col)  # Render option
            screen.blit(option, (self.pos[0] + (i * self.offset[0]), self.pos[1] + (i * self.offset[1])))

        if choice in self.locked:   # Disable selecting 'locked' options
            choice = 999

        return choice   # Return the selected option if space or similar is pressed. runMenus() runs code depending on what was selected


    def lock(self, val):
        self.locked.append(val)     # Locks an option so it can't be selected (e.g. greying out "continue" if you have nothing saved)

class Settings:
                                # Initialize settings on startup.
    def __init__(self):
        
        # settings.vvvvvv is a JSON file which stores the settings of your game when you quit.
        try:
            with open("settings.vvvvvv", 'r') as s:
                settings = json.loads(s.read())
                for saved in settings:
                    self.musicvolume = float(saved["musicvolume"])  # Volume for music
                    self.sfxvolume = float(saved["sfxvolume"])     # Volume for sound effects
                    self.musicpackSelected = int(saved["musicpackSelected"])  # Which music pack is selected?
                    self.msEnabled = str2bool(saved["msEnabled"])     # Extra timer info?
                    self.debugtools = str2bool(saved["debugtools"])   # Debug tools enabled?
                    self.invincible = str2bool(saved["invincible"])   # Invincibility enabled?
                    self.flippyboi = str2bool(saved["flippyboi"])     # Infinite flips enabled?
                    self.hudsize = int(saved["hudsize"])              # 0 is none, 1 is small, 2 is medium, 3 is large
                    self.fullscreen = str2bool(saved["fullscreen"])   # Fullscreen enabled?
                    self.AllSettings = [self.musicvolume, self.sfxvolume, self.musicpackSelected, self.msEnabled, self.debugtools, self.invincible, self.flippyboi, self.hudsize, self.fullscreen]
        except:
            self.AllSettings = [0.5,0.5,1,False,False,False,False,1,False]
        
        self.AllSettingsNames = ['musicvolume','sfxvolume','musicpackSelected','msEnabled','debugtools','invincible','flippyboi','hudsize','fullscreen']                
                                # Save the settings
    def save(self,Name,newValue):
        x = 0
        while x < len(self.AllSettingsNames):
            if self.AllSettingsNames[x] == Name:
                if x < 2:
                    self.AllSettings[x] += newValue
                    round(self.AllSettings[x], 1)
                else:
                    self.AllSettings[x] = newValue
            x += 1
        
        self.musicvolume = round(self.AllSettings[0], 1)
        self.sfxvolume = round(self.AllSettings[1], 1)
        self.musicpackSelected = self.AllSettings[2]
        self.msEnabled = self.AllSettings[3]
        self.debugtools = self.AllSettings[4]
        self.invincible = self.AllSettings[5]
        self.flippyboi = self.AllSettings[6]
        self.hudsize = self.AllSettings[7]
        self.fullscreen = self.AllSettings[8]
        
        x = 0
        settings = "[{\n"
        while x < len(self.AllSettings):
            settings += '"' + self.AllSettingsNames[x]  + '": "' + str(self.AllSettings[x]) + '"'
            if x < len(self.AllSettings) - 1:
                settings += ',\n'
            x += 1
        settings += '}]'
        with open("settings.vvvvvv", 'w') as s:
            s.writelines(settings)        
                                # SOUND EFFECTS

    def updateVolume(self):
        sfx_list = [sfx_bang,sfx_beep,sfx_blip,sfx_boop,sfx_flip,sfx_flop,sfx_hurt,sfx_menu,sfx_save,sfx_tele,sfx_secret,sfx_target,sfx_success]
        for sfx in sfx_list:
            pygame.mixer.Sound.set_volume(sfx, self.sfxvolume)

sfx_bang = pygame.mixer.Sound("./assets/sounds/bang.wav")
sfx_beep = pygame.mixer.Sound("./assets/sounds/beep.wav")
sfx_blip = pygame.mixer.Sound("./assets/sounds/blip.wav")
sfx_boop = pygame.mixer.Sound("./assets/sounds/boop.wav")
sfx_flip = pygame.mixer.Sound("./assets/sounds/flip.wav")
sfx_flop = pygame.mixer.Sound("./assets/sounds/flop.wav")
sfx_hurt = pygame.mixer.Sound("./assets/sounds/hurt.wav")
sfx_menu = pygame.mixer.Sound("./assets/sounds/menu.wav")
sfx_save = pygame.mixer.Sound("./assets/sounds/save.wav")
sfx_tele = pygame.mixer.Sound("./assets/sounds/tele.wav")
sfx_secret = pygame.mixer.Sound("./assets/sounds/secret.wav")
sfx_target = pygame.mixer.Sound("./assets/sounds/target.wav")
sfx_success = pygame.mixer.Sound("./assets/sounds/success.wav")
flipKeys = [pygame.K_SPACE, pygame.K_UP, pygame.K_DOWN, pygame.K_z, pygame.K_w, pygame.K_s, pygame.K_v, pygame.K_RETURN]  # Keys that make you flip

# Initial settings
player = Player()
setting = Settings()
bgCol = (0, 0, 0, 0)

setting.save('',0)
setting.updateVolume()
if setting.fullscreen:
    e = pygame.display.set_mode(screenSize, flags = pygame.HWSURFACE|pygame.FULLSCREEN)

sprites = []                        # Array of all the textures
groundTiles = []                    # Array of all ground tiles
backgroundTiles = []                # Array of all background tiles
spikeTiles = []                     # Array of all spike tiles
warpBGs = []                        # Array of warp backgrounds
teleporters = []                    # Array of teleporter frames
enemySprites = [[], []]             # Array of all the enemy textures
enemyCounts = [12, 4]               # How many enemies there are, for each type
largeHitboxes = [32, 34, 38, 28]    # Hitbox sizes of large 4x4 enemies
stars = []                          # Array of all the stars in the background
rects = []                          # Array of all the rectangles in the lab background
breakingPlatforms = {}              # Object containing the animation state of activated breaking platforms. The index is the coordinates
replaylist = []

cpRoom = ""  # Roomname of last checkpoint, for saving
area = ""    # Name of area, e.g. "The Space Station"
menutext = medfont.render(' ',1,WHITE)


# Global timers
starRate = 5            # How frequently background stars spawn (every nth frame)
starSpeed = 12          # How fast the average background star moves
menuBGSpeed = 2         # How fast the menu background moves
warpBGSpeed = 6         # How fast the warp background moves
breakSpeed = 6          # How quickly platforms break
enemyAnimation = 12     # How quickly enemies animate
conveyorAnimation = 10  # How quickly conveyors animate
conveyorSpeed = 4       # How fast conveyors move the player
lineWidth = 4           # Thickness of gravity lines
lineCooldown = 14       # Delay before being able to reuse a vertical gravity line
flashTime = 30          # How long the screen should flash white for. Value changes when using flash()


# When certain events are met, these will increment every frame until reaching their timer value above
globalTimer = 0
roomLoadTime = 0
flashTimer = 0
warpBGPos = 0
menuBGPos = random.randint(0, 2750)   # Shuffle where the menu starts a bit. Because why not.

flashing = False
savedGame = False
debug = False
levelnum = 0
savedVelocity = player.yacceleration  # Save the original player.velocity as it changes when touching a gravity line
palette = Palette().optimize()


def grey(val):  # Simple function to generate shades of grey
    return val, val, val


def snap(number):   # Snap to nearest grid space
    return math.floor(number/32)


def flash(time):    # Flash screen white for a specified of frames
    global flashing, flashTime
    flashing = True
    flashTime = time


def appendeach(arr, addto):   # Adds each element of list A to list B
    for e in arr:
        addto.append(e)
    return addto


def newroom(change, newPos, warpType):    # Change room relative to current one and set new position
    global player, room, globalTimer
    player.x = newPos[0]
    player.y = newPos[1]
    if room.meta["warp"] != warpType and player.winTimer == 0:
        globalTimer = 0
        reparseSpritesheets(0)
        loadroom(room.x + change[0], room.y + change[1])


def spawnBGStars():
    global starRate
    if globalTimer % starRate == 0:
        if room.meta["tileset"] <= 6 and room.meta["warp"] == 0:    # If space station tileset is used...
            stars.append([screenSize[0] + 5, random.randint(0, screenSize[1] - 32), random.randint(0, 50)])  # X, Y, Z, where Z position of star determines speed and brightness
        elif room.meta["tileset"] == 7 and room.meta["warp"] == 0:    # If warp zone tileset is used...
            stars.append([random.randint(0, screenSize[0]), screenSize[1], random.randint(0, 50)])  # Warp zone stars spawn from bottom instead of side
        elif room.meta["warp"] == 0:   # If the lab tileset is used...
            type = random.randint(1, 4)  # Add a background rectange going in a random cardinal direction
            if type == 1:
                rects.append([screenSize[0] + 5, random.randint(0, screenSize[1] - 32), 1])
            elif type == 3:
                rects.append([random.randint(0, screenSize[0]), screenSize[1] + 5, 3])
            elif type == 2:
                rects.append([-50, random.randint(0, screenSize[1] - 32), 2])
            elif type == 4:
                rects.append([random.randint(0, screenSize[0]), -50, 4])

def reparseSpritesheets(warp):
    global enemySprites, groundTiles, backgroundTiles, spikeTiles, warpBGHor, warpBGVer

    groundTiles = tileSheet.split(32, 32, 13, 32, 9, True)
    backgroundTiles = backgroundSheet.split(32, 32, 13, 32, 3, True)
    spikeTiles = spikeSheet.split(32, 32, 4, 32, 2)
    if warp == 1:
        warpBGHor = pygame.image.load("./assets/warpsHorizontal.png").convert()
##    elif warp == 2:
        warpBGVer = pygame.image.load("./assets/warpsVertical.png").convert() 
def switchtileset(row):  # Switches the currently loaded tileset. Runs on every room change

    # Start by loading sprites and adding to sprites array. Has to be done every room since textures and colors change
    # Sprites are reloaded each room so that they are reverted to their grey state and can be recolored
    # Because of how Pygame handles 'edited' textures, we unfortunately need to re-parse the spritesheets every load

    global sprites, groundTiles, backgroundTiles, spikeTiles, enemySprites, target
    sprites = []
    
    
    enemySprites[0] = enemySheetSmall.split(64, 64, 4, 64, enemyCounts[0])  # Append 2x2 enemies
    enemySprites[1] = enemySheetLarge.split(128, 128, 4, 128, enemyCounts[1])  # Append 4x4 enemies
    
                    # Which row of background tiles to use
                    
    if row == 8:    # Lab tileset
        bg = 1
    elif row == 7:  # Warp Zone tileset
        bg = 2
    else:
        bg = 0
    for i in range(13):
        sprites.append(groundTiles[row][i])  # Switch the ground tileset
    for i in range(13):
        sprites.append(backgroundTiles[bg][i])  # Switch the background tileset
    if bg == 1:
        for i in range(4):
            sprites.append(spikeTiles[1][i])  # Retexture spikes to second row of the spritesheet


    #  READ SPRITES.TXT FOR THE INDEX OF EACH OBJECT IN THE SPRITE ARRAY
    #  This probably isn't the ideal way of handling sprites, I was just inspired by how old SNES games do it
    else:
        appendeach(spikeTiles[0], sprites)  # Append spikes to 26-29. Assume regular tileset
    appendeach(playerSheet.split(player.width-2, player.height, 3), sprites)  # Append player sprites to 30-32
    appendeach(checkpointSheet.split(64, 64, 4), sprites)  # Append checkpoint sprites to 33-36
    appendeach(platformSheet.split(128, 32, 5), sprites)  # Append platforms to 37-41
    appendeach(conveyorSheet.split(32, 32, 8), sprites)  # Append conveyors to 42-49
    appendeach([0, 0], sprites)   # Editor-only objects, so here's an empty value
    appendeach(teleSheet.split(384, 384, 5), sprites)
    sprites.append(target)





def loadroom(rx, ry):  # Changes the current room
    global room, globalTimer
    globalTimer = 0
    room = Room(rx, ry)
    room.loadEnemies()


def setcheckpoint(xpos, ypos, saveflip, silent=False):  # Sets checkpoint save
    global checkpoint, room, cpRoom
    if not silent:
        sfx_save.play()
    checkpoint = [room.x, room.y, xpos, ypos, saveflip]
    cpRoom = room.meta["name"]


def parsecoords(coords):  # Parses coordinates from string (in object keys)
    cx, cy, cz = str(coords).split(",")
    return [int(cx), int(cy), int(cz)]


def stringcoords(coords, Z=0):   # Change coordinates back to string
    return str(coords[0]) + "," + str(coords[1]) + "," + str(Z)


def issolid(obj, boundry=False):     # Check if object is 'solid'
    return 12 >= obj >= 0 or 37 <= obj <= 40 or 42 <= obj <= (49+boundry)


def isspike(obj):     # Check if object is a spike
    return 29 >= obj >= 26


def solidblock(blocksize, tx, ty, nextframe = False):  # When the player comes in contact with a solid block
    global standingOn, player
    isstanding = False  # Guilty until proven innocent
    for blockTile in range(1, blocksize + 1):   # For larger objects (e.g. platforms), check each tile
        gridspace = tx + (32 * (blockTile - 1))

        if player.touching([gridspace, ty],nextframe = True):  # If block is next to you

            if player.x < gridspace:
                player.blocked[1] = True  # Block right
            elif player.x >= gridspace:
                player.blocked[0] = True  # Block left

        if (snap(gridspace) == standingOn[0] or snap(gridspace) == standingOn[0] + 1) and snap(ty) == \
                standingOn[1] and 36 > player.x + 2 - gridspace > -46:
            player.grounded = True     # If you're standing on a block...
            isstanding = True   # Looks like you're standing!
            player.coyoteTimer = 0      # Reset coyote timer
            
    return isstanding

     # When the player's position and acceleration values cause 
def getobj(coords, Z=0):   # Get object at specified coords
    global room
    try:
        return room.tiles[stringcoords(coords, Z)]
    except KeyError:
        return -1


def collision(topA, bottomA, topB, bottomB):  # Check for collision between two hitboxes
    return topA[0] < bottomB[0] and bottomA[0] > topB[0] and topA[1] < bottomB[1] and bottomA[1] > topB[1]


def roundto(num, target):   # Rounds number to nearest multiple of Y
    return num + (target - num) % target


def getMusic(menu=False):   # Figure out what music should be playing
    global music, levelFolder, setting
    if menu: song = "menu"
    else:   # Find song to use based on current level
        for i in levels:
            if i["folder"] == levelFolder:
                song = i["music"]
    try: pygame.mixer.music.load("./assets/musicpack" + str(setting.musicpackSelected) +"/" + song + ".ogg")
    except pygame.error: pygame.mixer.music.load("./assets/musicpack1/space.oggogg")
    pygame.mixer.music.play(-1)


def switchdirection(data, w, h, includeSpikes=False):   # Change enemy/platform direction
    result = [False, False]
    for i in range(3):  # Iterate through the 3 z layers

        gridX, gridY = [snap(data[0]), snap(data[1])]

        if (data[2] > 0 and issolid(getobj([gridX + w, gridY], i), True)) or \
                (data[2] < 0 and issolid(getobj([gridX, gridY], i), True)) or \
                (data[2] < 0 and getobj([gridX-3, gridY], 2) == 37):
            result[0] = True   # Flip X

        elif includeSpikes and ((data[2] > 0 and isspike(getobj([gridX + w, gridY], 1))) or \
                (data[2] < 0 and isspike(getobj([gridX, gridY], 1)))):
            result[0] = True   # Flip X, if includeSpikes is enabled

        if (data[3] > 0 and issolid(getobj([gridX, gridY + h], i), True)) or \
                (data[3] < 0 and issolid(getobj([gridX, gridY], i), True)):
            result[1] = True   # Flip Y

        elif includeSpikes and ((data[3] > 0 and isspike(getobj([gridX, gridY + h], 1))) or \
                (data[3] < 0 and isspike(getobj([gridX, gridY], 1)))):
            result[1] = True   # Flip Y, if includeSpikes is enabled

    return result


def renderHUD():    # Displays time + FPS ingame, plus lots of debug info if F3 is pressed
    global setting
    gameTime = str(player.mins) + ":" + str(player.secs).zfill(2)
    if setting.msEnabled: gameTime += "." + str(round(player.frames / 60 * 100)).zfill(2)
    if setting.debugtools:
        fpsExtension = "(" + str(framerate) + ")"
    else:
        fpsExtension = ''
    if setting.hudsize == 3:                                  # Small font
        timer = font.render(gameTime, 1, WHITE)
        fpsCount = font.render(str(int(clock.get_fps())) + " FPS" + fpsExtension, 1, WHITE)
    elif setting.hudsize == 2:                                # Medium font
        timer = medfont.render(gameTime, 1, WHITE)
        fpsCount = medfont.render(str(int(clock.get_fps())) + " FPS" + fpsExtension, 1, WHITE)
    elif setting.hudsize == 1:
        timer = smallfont.render(gameTime, 1, WHITE)  # Render timer
        fpsCount = smallfont.render(str(int(clock.get_fps())) + " FPS" + fpsExtension, 1, WHITE)  # Render FPS count
    else:
        timer = smallfont.render('', 1, WHITE)
        fpsCount = smallfont.render('', 1, WHITE)
    screen.blit(timer, (10, 10))  # Display clock
    screen.blit(fpsCount, (10, setting.hudsize * 5 + 25))  # Display FPS counter

    if debug and setting.debugtools:   # Toggle with F3
        roomStr = str(len(room.tiles)) + "/" + str(len(room.platforms)) + "/" + str(len(room.enemies)) + "/" + str(len(room.lines))

        deathCount = smallfont.render("Deaths: " + str(player.deaths), 1, WHITE)
        flipCount = smallfont.render("Flips: " + str(player.flips), 1, WHITE)
        roomSpeed = smallfont.render("Room Load: " + str(roomLoadTime) + "ms", 1, WHITE)
        starCount = smallfont.render("BG: " + str(len(stars)) + "/" + str(len(rects)) + "/" + str(warpBGPos), 1, WHITE)
        roomData = smallfont.render("Data: " + roomStr, 1, WHITE)
        roomPos = smallfont.render("Pos: " + str(player.x) + "," + str(player.y) + "/" + str(room.x) + "," + str(room.y), 1, WHITE)

        screen.blit(deathCount, (10, 40 + 10 * setting.hudsize))
        screen.blit(flipCount, (10, 60 + 10 * setting.hudsize))
        screen.blit(starCount, (10, 80 + 10 * setting.hudsize))
        screen.blit(roomSpeed, (10, 100 + 10 * setting.hudsize))
        screen.blit(roomPos, (10, 120 + 10 * setting.hudsize))
        screen.blit(roomData, (10, 140 + 10 * setting.hudsize))


def checksave():    # Load save file
    global savedGame
    try:  # Try to open and parse save file
        with open('save.vvvvvv', 'r') as savedata:
            savedGame = json.loads(savedata.read())
    except FileNotFoundError:
        savedGame = False

def buildmenu():    # Builds the main menu
    global menu, savedGame, menutext, setting, globalTimer
    globalTimer = 0
    checksave()
    reparseSpritesheets(0)
    menutext = medfont.render(' ',1,WHITE)
    menu = Menu("menu", ["new game", "continue", "play replay", "level editor", "settings", "quit"], 225)
    del setting
    setting = Settings()
    if not savedGame:
        menu.lock(1)    # Disable "continue" option if no saved game

def runMenus():   # Run code depending on what menu option is selected
    global menu,area,player,key,ingame,checkpoint,levelFolder,cpRoom,epstein_didnt_kill_himself,levelnum,menutext,replaylist
    option = menu.run()

    if menu.name == "pause":    # Pause menu

        if setting.debugtools or setting.invincible or setting.flippyboi:
            menu.lock(1)  # Disable saving when cheating.
        if player.winTimer > 0:
            menu.lock(2)  # Disable retry when in a cutscene.
        
        if option == 0:
            player.buffer = -999
            ingame = True   # Unpause

        if option == 1:
            sfx_boop.play()     # Save game
            menu.lock(1)
            flash(6)
            checkpoint[4] += 0  # Convert bool to number since JSON uses lowercase true/false
            levelIndex = 0
            for i in range(len(levels)):
                if levels[i]["folder"] == levelFolder: levelIndex = i
            saveJSON = {"stage": levelIndex, "checkpoint": checkpoint, "room": cpRoom, "deaths": player.deaths, "flips": player.flips, "time": [player.mins, player.secs, player.frames]}
            with open("save.vvvvvv", 'w') as data:
                json.dump(saveJSON, data)
            checksave()
            
        if option == 2:
            ingame = True
            temp2 = 0
            if player.replay > 0:
                temp = player.inputs
                temp1 = player.frameinput
                temp2 = 1
            startlevel(levels[levelnum])
            if temp2 == 1:
                player.inputs = temp
                player.frameinput = temp1
                player.replay = 1
       
        if option == 3:     # Quit stage and return to main menu
            sfx_hurt.play()
            player = Player()
            buildmenu()
            getMusic("menu")

        if option == 4:     # Quit game
            epstein_didnt_kill_himself = False


    elif menu.name == "levels":     # Level select

        screen.blit(levelSelect, ((screenSize[0] / 2) - (levelSelect.get_width() / 2), 180))    # Display "select stage"

        for i in range(len(levels) + 1):    # Build menu dynamically depending on the contents of levels.vvvvvv
            if option == i or key[pygame.K_ESCAPE]:
                if i == len(levels) or key[pygame.K_ESCAPE]:
                    buildmenu()     # Return to main menu upon pressing "back" or escape
                    sfx_menu.play()
                else:
                    levelnum = i
                    startlevel(levels[i])   # Start the selected level

        # Display high scores in the bottom left corner
        if menu.selected < len(levels) and menu.name == "levels":  # Checking menu.name a second time fixes a small visual bug when pressing "back" (see for yourself)
            bestTime = "Best Time: **:**.**"
            leastDeaths = "Not yet completed"
            for r in records:
                if r[0] == levels[menu.selected]["folder"]:   # If high score is saved for the selected menu
                    bestTime = "Best Time: " + str(r[1][0]) + ":" + str(r[1][1]).zfill(2) + "." + str(round(r[1][2] / 60 * 100)).zfill(2)
                    leastDeaths = "Least Deaths: " + str(r[2])
            bestTimeMsg = medfont.render(bestTime, 1, WHITE)
            leastDeathMsg = medfont.render(leastDeaths, 1, WHITE)
            screen.blit(bestTimeMsg, (20, screenSize[1] - 60))
            screen.blit(leastDeathMsg, (20, screenSize[1] - 35))

    elif menu.name == "menu":
        
            
        # Display + center the logo and subtitle
        screen.blit(logo, ((screenSize[0] / 2) - (logo.get_width() / 2), 125))
        screen.blit(subtitle, ((screenSize[0] / 2) - (subtitle.get_width() / 2), 225))

        if option == 0:     # "New game" - Display the level select screen
            sfx_save.play()
            levelList = []
            for i in levels:
                levelList.append(i["name"].lower().replace("the ", ""))
            levelList.append("back")
            menu = Menu("levels", levelList, 100)
        version = "v1.6"     # Display the version number only if continue isn't selected.
        if savedGame:   # If you have a saved game and "continue" is pressed, pick up from where you left off
            savedStage = levels[savedGame["stage"]]
            if menu.selected == 1:  # Display some info about your saved game when hovering over
                saveInfo = levels[savedGame["stage"]]["name"].replace("The ", "")
                if len(savedGame["room"]):
                    saveInfo += " - " + savedGame["room"]
                saveInfo += " (" + str(savedGame["time"][0]) + ":" + str(savedGame["time"][1]).zfill(2) + ")"
                saveMsg = medfont.render(saveInfo, 1, WHITE)
                screen.blit(saveMsg, (20, screenSize[1] - 35))
            else:
                temp = medfont.render(version, -1, pygame.Color(85, 85, 125))
                screen.blit(temp, (20, screenSize[1] - 35))
            if option == 1:     # Load your saved game using the details in save.vvvvvv
                check = savedGame["checkpoint"]
                area = savedStage["name"]
                levelFolder = savedStage["folder"]
                loadroom(check[0], check[1])
                player.x = check[2]
                player.y = check[3]
                player.deaths = savedGame["deaths"]
                player.flips = savedGame["flips"]
                player.mins = savedGame["time"][0]
                player.secs = savedGame["time"][1]
                player.frames = savedGame["time"][2]
                player.replay = -1
                if check[4]: player.flip(True)
                checkpoint = check
                cpRoom = room.meta["name"]
                ingame = True
                getMusic()
                sfx_save.play()
        else:
                temp = medfont.render(version, -1, pygame.Color(85, 85, 125))
                screen.blit(temp, (20, screenSize[1] - 35))            
        if option == 2:
            sfx_menu.play()
            replaylist = []
            for file in os.listdir("replays"):
                if file.endswith(".replay"):
                    file = file.replace(';',':')
                    replaylist.append(file.replace('.replay',''))
            replaylist.append("back")
            menu = Menu("replays", replaylist)
                
        if menu.selected == 2:
            screen.blit(menutext, (20, screenSize[1] - 35))
        if option == 3:
            import editor
            editor.done = True
            # epstein_didnt_kill_himself = False
            # editor = importlib.reload(editor)
            #importlib.reload(editor)

        if option == 4:
            sfx_menu.play()
            setting.save('',0)
            menu = Menu("settings", ["audio settings", "video settings", "gameplay settings", "back"])
        if option == 5:     # Quit
            epstein_didnt_kill_himself = False

    elif menu.name == "replays":  # Replay settings

        if len(replaylist) == 10:
            temp = medfont.render('Replay folder full!', -1, WHITE)
            screen.blit(temp, (20, screenSize[1] - 35))
        if option < len(replaylist) - 1:
            sfx_menu.play()
            try:
                with open('./replays/' + replaylist[option].replace(':',';') + '.replay',"r") as f:
                    levelnum = int(f.readline())
                    startlevel(levels[levelnum])
                    
                    setting.debugtools = str2bool(f.readline())
                    setting.invincible = str2bool(f.readline())
                    setting.flippyboi = str2bool(f.readline())
                    player.replay = 1
                    x = 0
                    player.inputs = []
                    player.frameinput = []
                    while x >= 0:
                        player.inputs.append(f.readline(4))
                        try:
                            player.frameinput.append(int(f.readline()))
                        except ValueError:
                            x = -69
                        x += 1
                player.frameinput.append(0)
            except UnboundLocalError:
                menutext = medfont.render("An error has occured.. :(", 1, WHITE)
        elif option == len(replaylist) - 1:
            sfx_menu.play()
            buildmenu()
        
    elif menu.name == "settings":   # All settings [ Audio , Video, Gameplay ]
        if option == 0:
            menu = Menu("audio", ["music volume", "sfx volume", "music packs", "back"])
            sfx_menu.play()
        elif option == 1:
            menu = Menu("video", ["Toggle fullscreen", "back"])
            #prog = subprocess.Popen(['python', 'editor16x9.py'])
            
            sfx_menu.play()
        elif option == 2:
            menu = Menu("gameplay", ["More timer info", "HUD size", "Cheats", "back"])
            sfx_menu.play()
        elif option == 3:
            sfx_menu.play()         
            buildmenu()

    elif menu.name == "audio":  # All Audio settings --------
        if option == 0:
            menu = Menu("musicvolume", ["+","return","-"])
            sfx_menu.play()
        elif option == 1:
            menu = Menu("sfxvolume", ["+","return","-"])
            sfx_menu.play()
        elif option == 2:
            menu = Menu("musicpack", ["+","return","-"])
            sfx_menu.play()
        elif option == 3:
            menu = Menu("settings", ["audio settings", "video settings", "gameplay settings", "back"])
            sfx_menu.play()

                
    elif menu.name == "musicvolume":    # Music settings
        vol_str = "{:.0%}".format(setting.musicvolume)
        volume = font.render(vol_str, 1, CYAN)
        screen.blit(volume, ((screenSize[0] / 2) - (volume.get_width() / 2), 150))
        
        if option == 0 and setting.musicvolume < 0.95:
            sfx_menu.play()
            setting.save('musicvolume',0.1)
        if option == 1:
            sfx_menu.play()
            menu = Menu("audio", ["music volume", "sfx volume", "music packs", "back"])
        if option == 2 and setting.musicvolume > 0.05:
            sfx_menu.play()
            setting.save('musicvolume',-0.1)
    
    elif menu.name == "sfxvolume":  # Sound settings
        vol_str = "{:.0%}".format(setting.sfxvolume)
        volume = font.render(vol_str, 1, CYAN)
        screen.blit(volume, ((screenSize[0] / 2) - (volume.get_width() / 2), 150))
            
        if option == 0 and setting.sfxvolume < 0.95:
            sfx_menu.play()
            setting.save('sfxvolume',0.1)
        if option == 1:
            sfx_menu.play()
            menu = Menu("audio", ["music volume", "sfx volume", "music packs", "back"])
        if option == 2 and setting.sfxvolume > 0.05:
            sfx_menu.play()
            setting.save('sfxvolume',-0.1)
        setting.updateVolume()

    elif menu.name == "musicpack":
        musicSelect = "Music selected: Pack " + str(setting.musicpackSelected)
        mus = font.render(musicSelect, 1, CYAN)
        screen.blit(mus, ((screenSize[0] / 2) - (mus.get_width() / 2), 150))
        
        if option == 0:
            try: pygame.mixer.music.load("./assets/musicpack" + str(setting.musicpackSelected + 1) +"/" + "space.ogg")
            except pygame.error: setting.musicpackSelected -= 1
            setting.save('musicpackSelected',setting.musicpackSelected + 1)
            sfx_menu.play()
            getMusic()
        if option == 1:
            sfx_menu.play()
            getMusic(1)
            menu = Menu("audio", ["music volume", "sfx volume", "music packs", "back"])
        if option == 2:
            try: pygame.mixer.music.load("./assets/musicpack" + str(setting.musicpackSelected - 1) +"/" + "space.ogg")
            except pygame.error: setting.musicpackSelected += 1
            setting.save('musicpackSelected',setting.musicpackSelected - 1)
            sfx_menu.play()
            getMusic()

    elif menu.name == "video":      # All video settings -------
        if option == 0:
            sfx_menu.play()
            if setting.fullscreen:
                e = pygame.display.set_mode(screenSize)
                setting.save('fullscreen',False)
            else:
                e = pygame.display.set_mode(screenSize, flags = pygame.FULLSCREEN|pygame.HWSURFACE)
                setting.save('fullscreen',True)
        if option == 1:
            sfx_menu.play()
            menu = Menu("settings", ["audio settings", "video settings", "gameplay settings", "back"])
            
    elif menu.name == "gameplay":   # All gameplay settings -----
        renderHUD()
        if menu.selected == 0:
            if setting.msEnabled:
                ms = "Timer will show milliseconds"
            else:
                ms = "Timer will only show minutes and seconds"
            temp = medfont.render(ms, 1, WHITE)
            screen.blit(temp, (20, screenSize[1] - 35))
        if option == 0 and setting.msEnabled == False:
            sfx_save.play()
            setting.save('msEnabled',True)
        elif option == 0 and setting.msEnabled == True:
            sfx_hurt.play()
            setting.save('msEnabled',False)
        if menu.selected == 2:
            temp = medfont.render("Note: Records aren't saved if cheats are enabled!", 1, WHITE)
            screen.blit(temp, (20, screenSize[1] - 35))
        if option == 1:
            sfx_menu.play()
            menu = Menu("hudsize", ["none", "small", "medium", "large"])
        if option == 2:
            sfx_tele.play()
            menu = Menu("cheats", ["debug tools", "invincibility mode", "flip in midair", "back"])
        if option == 3:
            sfx_menu.play()
            menu = Menu("settings", ["audio settings", "video settings", "gameplay settings", "back"])

    elif menu.name == "hudsize": # HUD Size settings
        renderHUD()
        if menu.selected == 0:
            setting.save('hudsize',0)
        if menu.selected == 1:
            setting.save('hudsize',1)
        if menu.selected == 2:
            setting.save('hudsize',2)
        if menu.selected == 3:
            setting.save('hudsize',3)
        if option <= 3:
            menu = Menu("gameplay", ["ms display", "HUD size", "Cheats", "back"])
            sfx_save.play()

            
    elif menu.name == "cheats": # Cheat settings
        if menu.selected == 0:  # Debug Tools
            if setting.debugtools == True:
                dbt = "The OG cheats from GD Colon are enabled"
            else:
                dbt = "All debug features are disabled"
            temp = medfont.render(dbt, 1, WHITE)
            screen.blit(temp, (20, screenSize[1] - 35))
        if option == 0 and setting.debugtools == False:
            sfx_save.play()
            setting.save('debugtools',True)
        elif option == 0 and setting.debugtools == True:
            sfx_hurt.play()
            setting.save('debugtools',False)
            
        if menu.selected == 1: # Invincibility Mode
            if setting.invincible == True:
                inv = "Spikes need not apply"
            else:
                inv = "Pro tip: Spikes and enemies kill you"
            temp = medfont.render(inv, 1, WHITE)
            screen.blit(temp, (20, screenSize[1] - 35))
        if option == 1 and setting.invincible == False:
            sfx_save.play()
            setting.save('invincible',True)
        elif option == 1 and setting.invincible == True:
            sfx_hurt.play()
            setting.save('invincible',False)
            
        if menu.selected == 2: # Infinite Flips
            if setting.flippyboi == True:
                flip = "Flip in midair!"
            else:
                flip = "You regain your flip when you touch the ground"
            temp = medfont.render(flip, 1, WHITE)
            screen.blit(temp, (20, screenSize[1] - 35))
        if option == 2 and setting.flippyboi == False:
            sfx_save.play()
            setting.save('flippyboi',True)
        elif option == 2 and setting.flippyboi == True:
            sfx_hurt.play()
            setting.save('flippyboi',False)
        if option == 3:
            menu = Menu("gameplay", ["ms display","HUD size", "Cheats", "back"])
            sfx_menu.play()
            

def startlevel(levelObj):   # Starts a stage
    global checkpoint, levelFolder, ingame, player, area, cpRoom, fullReplay
    reparseSpritesheets(0)
    player = Player()   # Create fresh new player
    levelFolder = levelObj["folder"]
    area = levelObj["name"]
    loadroom(levelObj["startingRoom"][0], levelObj["startingRoom"][1])
    player.x = levelObj["startingCoords"][0]
    player.y = levelObj["startingCoords"][1]
    checkpoint = [room.x, room.y, player.x, player.y, player.flipped]
    cpRoom = room.meta["name"]
    ingame = True   # Begin
    sfx_save.play()
    getMusic()

for i in range(30):  # Prepare some stars for the normal background
    stars.append([random.randint(25, screenSize[0] - 25), random.randint(0, screenSize[1] - 32), random.randint(0, 50)])
    if not i % 5:   # Prepare a rectangle for the lab background on every 5th iteration
        rects.append([random.randint(0, screenSize[0]), random.randint(0, screenSize[1]), random.randint(1, 4)])

buildmenu()
pygame.mixer.music.stop()
#####################
#     MAIN LOOP     #
#####################

while epstein_didnt_kill_himself:   # Runs every frame @ 60 FPS

    key = pygame.key.get_pressed()          # List of pressed keys
    mouse = pygame.mouse.get_pressed()      # List of pressed mouse buttons
    events = pygame.event.get()             # List of keyboard/mouse/misc events fired on current frame
    if ingame:

        player.refresh()
        standingOn = player.getStandingOn()

        # I split the room code across multiple functions to keep things tidy
        room.renderBG()     # Background color, stars, texture, etc
        room.checkLines()   # Gravity line collisions and rendering
        room.run()          # Render all textures and run code depending on each object ID
        spawnBGStars()      # Background details, dependent on tileset
        player.getInput()   # Gets inputs on current frame
        player.exist()      # Player physics and more
        room.renderName(font, screenSize, screen)   # Layer above player

        if player.winTimer == 0:
            renderHUD()

        # Increment global timer used for animations.
        # Resets when transitioning to a new room, so animations start at the beginning of the loop as soon as the animation appears on-screen
        globalTimer += 1

    else:
        runMenus()   # Menus!
        try:
            pygame.mixer.music.set_volume(setting.musicvolume)
        except pygame.error:
            print('Something went wrong when switching to the main game from the editor')
            
            framerate = 60  # In Frames per seconds.

        if setting.invincible or setting.flippyboi:
            Cheater = font.render('C', 1, RED)
            if not setting.debugtools:
                framerate = 60
        elif setting.debugtools:
            Cheater = font.render('DEBUG', 1, WHITE)  # Render
        else:
            Cheater = font.render('', 1, WHITE)
            framerate = 60
        

    screen.blit(Cheater, (screenSize[0] - 5 - Cheater.get_width(), 10))
    for event in events:
        # print(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_p:
                if ingame or menu.name == "pause":   # If you're ingame...
                    ingame = not ingame              # Pause/unpause gameplay
                    menu = Menu("pause", ["continue", "save", "retry", "menu", "quit"], 0, False)   # Build pause menu
            if setting.debugtools: 
                if event.key == pygame.K_F3:
                    debug = not debug   # Toggle debug menu upon pressing F3
                if event.key == pygame.K_k:
                    if framerate > 20:
                        framerate -= 5
                    elif framerate > 10:
                        framerate -= 2
                    elif framerate > 1:
                        framerate -= 1
                if event.key == pygame.K_l:
                    if framerate < 10:
                        framerate += 1
                    elif framerate < 20:
                        framerate += 2
                    elif framerate >= 20:
                        framerate += 5
                if event.key == pygame.K_SEMICOLON:
                    framerate = 60
        elif event.type == pygame.VIDEORESIZE:
            getMusic(True)
        elif event.type == pygame.QUIT:   # Allow quitting
            epstein_didnt_kill_himself = False  # Pygame disagrees with this and closes the program
            
    if flashing:    # If the flash() function is active, fill the screen with white
        screen.fill(WHITE)
        flashTimer += 1
        if flashTimer > flashTime:
            flashTimer = 0
            flashing = False

    pygame.display.flip()   # Display everything
    clock.tick(framerate)  # 60 FPS

pygame.quit()   # Adios!

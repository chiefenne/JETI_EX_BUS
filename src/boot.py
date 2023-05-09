# boot.py -- run on boot-up
# this script is executed when the pyboard boots up. It sets
# up various configuration options for the pyboard.
# can run arbitrary Python, but best to keep it minimal

# IMPORTANT:
# When the pyboard boots up, it needs to choose a filesystem to boot from.
# If there is no SD card, then it uses the internal filesystem /flash as the boot filesystem,
# otherwise, it uses the SD card /sd.
# After the boot, the current directory is set to one of the directories above.
# If needed, you can prevent the use of the SD card by creating an empty file called /flash/SKIPSD.
# If this file exists when the pyboard boots up then the SD card will be skipped and
# the pyboard will always boot from the internal filesystem
# (in this case the SD card won’t be mounted but you can still mount and
# use it later in your program using os.mount).

import usys as sys
from os import listdir as ls
# print (' ')
# print ('INFO (boot.py): Imported os and os.listdir as ls')
# print ('INFO (boot.py): You can use now ls() to list directory contents.')
# print (' ')

# check platform
print('INFO (boot.py): Microcontroller platform --> {}'.format(sys.platform))
print(sys.implementation)

# main script to run after this one
# if not specified "main.py" will be executed

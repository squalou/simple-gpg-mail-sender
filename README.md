# simple-gpg-mail-sender

a python minimalistic tk gui for sending securely crypted attachements

## security for noobs

Imagine a non-technical person, wanting to send to you securely a document. Say .. your grandmother, or some of you customers depending on the situation.

For those situation, here's a quick and not-so-dorty solution.

- customize two lines in this project to fit you needs ( = your GPG key id, your associated email)
- install gpg on the person's computer (windows / linux tested)
- install this python script on the computer (see below)
- run it, add a file, send, done !

The idea here is to have one custome tool dedicated to send emails securely to ONE recipient, hardcoded in the tool ... because it's my usecase.

## disclaimer

target audience was initially french only, so most mesasges are hardcoded in french.

## prerequisites for you : the email recipient

You should now basics about python installation, pip, and virtualenv, if not browse the web for it. No development skills required, but you need to install and run python.

You should now about GPG, have a public/private keypair ready, and publish it (recommended on pool.sks-keyservers.net, else you'll need to edit `keyservers` in GpgMail.py)

## prerequisite on sender's computer

install GPG

### linux

should be easy enough, if not installed by default for your package manager day-to-day use. (apt-get install or yum, or pacman, choose your flavor)

### windows

GPG4Win is [available here](https://gpg4win.org/download.html), install it.

## prepare the software

On a computer *using the same OS as the target OS* : install python >= 3.6

Create a virtualenc, run `pip install -r requirements.txt`

Check it looks like it works : python GpgMail.py

## customize it for you

Edit the head of GpgMail.py :

```python
# customize these 2 lines for emails *recipient*'s gpg public key id
GPG_KEY_ID = "0x1254798657465446"
GPG_DEST_EMAIL = "someone@nowhere.com"
```

***note** the `Ox` in front of the key id, don't forget it or nothing will work.

## package it

I personnaly use `pyinstaller`. Example below is for linux users but things are the same on windows, excpet for the zip command.

```bash
pip install pyinstaller
pyinstaller -w GpgMail.py

cd dist
gpgmail.zip GpgMail

```

You'll get a "dist" directory containing a "GpgMail" directory and gpgmail.zip : bring the latter to the sender's computer.

## run on sender's computer

### install

Unzip gpgmail.zip somewhere, run `GpgMail` from inside or `GpgMail.exe` on windows ... and proceed to first run configuration.

### configure

The sender need an smtp server to send emails, obviously :)

On first run, a configuration window will appear, fill in the fields :

- smtp server and port
- smtp user
- smtp password (stored crypted, but displayed clearly on first run)
- sender's email

### use

Easy as 1, 2, 3

- 1 : add a file using the dedicated button
- 2 : add an object to the mail, and maybe some text
- 3 click send

File is crypted, mail is sent, and only the recipient can decipher it. Profit.

## Troubleshooting

logs are available alongside GpgMail executable (`secure-mail.log`)

You can increse verbosity by changing loglevel : in `_gpg\secure-mail.conf` change log_level to `10` for debug. (levels are standard python logging values : 50 for less verbose to 10 for debug, 20 is INFO which is also the default value)

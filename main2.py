import os
import speech_recognition as sr
import wave
import time
import json
import cognitive_face as CF
import itchat
import sys
from itchat.content import *
from PIL import Image
import threading
import RPi.GPIO as GPIO
import struct
import sys
import urllib
from xml.etree import ElementTree
import wave
import http.client


def send_message(message, userId):
	itchat.send(message, toUserName = userId)

def send_picture(filename,userId):
	itchat.send_image(filename, toUserName = userId)

def send_file(filename,userId):
	itchat.send_file(filename, toUserName = userId)

def record_btn(userID):
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	if GPIO.input(13) == GPIO.HIGH:
		print("record will take place")		
			#os.system('arplay ')
		os.system("arecord -d 5 msg.wav ")
		print("record end")
		send_file("msg.wav",userID)

def GetFileListFromDir(dir):
	l = []
	for p, d, f in os.walk(dir):
		for fname in f:
			l.append(os.path.join(p,fname))
	return l

def CheckGroupIdExistStatus(groupId):
	for info in CF.person_group.lists():
		if info['personGroupId'] == groupId:
			return True
	return False

def trainface():
	KEY = "232d6ece9aad407c89067c63be83c3cf"
	CF.Key.set(KEY)
# create group and person
	personGroupId = "leiyiran" 
# Valid format should be a string composed 
#by numbers, English letters in lower case,
# '-', '_', and no longer than 64 characters. 
	if not CheckGroupIdExistStatus(personGroupId):
		CF.person_group.create(personGroupId,"leiyiran and his friend and family")
	user1 = CF.person.create(personGroupId,"a smart and genius boy")
# add face
	friendImageDir = "faceRecognition/img/person"
	for fname in GetFileListFromDir(friendImageDir):
		CF.person.add_face(fname, personGroupId, user1['personId'])
# train
	CF.person_group.train(personGroupId)
	trainingStatus = "running"
	while(True):
		trainingStatus = CF.person_group.get_status(personGroupId)
		if trainingStatus['status'] != "running":
			print(trainingStatus)
			break

def wechatreply(Id):	
	#make dirs for downloading pictures and recordings
	if not os.path.exists('./picture'): 
		os.mkdir('./picture')

	if not os.path.exists('./recording'):
		os.mkdir('./recording')

	@itchat.msg_register([TEXT,PICTURE,RECORDING], isFriendChat=True)
	def tocaller(msg):
		#if master send two message at once, deal it with queue
		if msg['Type'] == 'Text': #if master send a short message, put it into the queue
			print("Master：" + msg['Text']) 
			text_to_speech(msg['Text'])
			os.system("aplay masterreply.wav")

		if msg['Type'] == 'Picture':
			fileName = './faceRecognition/img/person/' + msg['FileName']
			with open(fileName, 'wb') as f: #download file
				f.write(msg['Text']()) 
			print("photo received! Trainning...")
			trainface();
			send_message("photo has been trained!",Id)


		if msg['Type'] == 'Recording':
			fileName = './recording/' + msg['FileName']
			with open(fileName, 'wb') as f: # download file
				f.write(msg['Text']())
			print("Master send a voice")
			os.system('mplayer '+ fileName) # play this audio
			
		del msg 
	itchat.run()

#pin: the GPIO pin you choose
#times: times to blink
#delay: duration between blinking
def light(pin, times, delay):
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(pin,GPIO.OUT)
	onoff = GPIO.LOW
	
	i = 0
	while i < times:
		if onoff == GPIO.LOW:
			onoff = GPIO.HIGH
		else:
			onoff = GPIO.LOW
		GPIO.output(pin, onoff)
		time.sleep(delay)
		i += 1
	GPIO.output(pin, GPIO.LOW)

def light_out(pin):
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(pin,GPIO.OUT)
	GPIO.output(pin,GPIO.LOW)


#if x^2 + y^2 + z^2 > threshold
#somebody knock the door
def knock_btn():
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(7, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	while 1:
		time.sleep(0.1)
		if GPIO.input(7) == GPIO.HIGH:
			break


#control the steering gear
def open_door():
	GPIO.setup(12,GPIO.OUT)
	p = GPIO.PWM(12,50)
	p.start(0)
	global onoff,dc, dir
	onoff = GPIO.LOW
	dc = 0
	dir = 5
	while 1:
		if dc > 125:
			dir = -5
		elif dc < 10:
			dir = 5
		dc = dc + dir
		p.ChangeDutyCycle( dc/10 )
		if GPIO.input(16) == GPIO.HIGH:
			break


def text_to_speech(text):
	apiKey = "34c7815245934e4a8e088956af4e62d7"
	headers = {"Ocp-Apim-Subscription-Key": apiKey}
	AccessTokenHost = "api.cognitive.microsoft.com"
	path = "/sts/v1.0/issueToken"
	conn = http.client.HTTPSConnection(AccessTokenHost)
	conn.request("POST", path, '', headers)
	response = conn.getresponse()
	data = response.read()
	conn.close()
	accesstoken = data.decode("UTF-8")
#print ("Access Token: " + accesstoken)
	body = ElementTree.Element('speak', version='1.0')
	body.set('{http://www.w3.org/XML/1998/namespace}lang', 'en-us')
	voice = ElementTree.SubElement(body, 'voice')
	voice.set('{http://www.w3.org/XML/1998/namespace}lang', 'en-us')
	voice.set('{http://www.w3.org/XML/1998/namespace}gender', 'Male')
	voice.set('name', 'Microsoft Server Speech Text to Speech Voice (en-US, BenjaminRUS)')
	voice.text = text
	print(body)
	headers = {"Content-type": "application/ssml+xml", 
				"X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm", 
				"Authorization": "Bearer " + accesstoken, 
				"X-Search-AppId": "07D3234E49CE426DAA29772419F436CA", 
				"X-Search-ClientID": "1ECFAE91408841A480F00935DC390960", 
				"User-Agent": "TTSForPython"}
#Connect to server to synthesize the wave
	print ("\nConnect to server to synthesize the wave")
	conn = http.client.HTTPSConnection("speech.platform.bing.com")
	conn.request("POST", "/synthesize", ElementTree.tostring(body), headers)
	response = conn.getresponse()
	print(response.status, response.reason)
	data = response.read()
	conn.close()
	print("The synthesized wave length: %d" %(len(data)))
#Write data in wav file
	f = wave.open(r"masterreply.wav","wb")
	f.setnchannels(1)
	f.setsampwidth(2)
	f.setframerate(16000)
	f.writeframes(data)
	f.close()

# Start from here.......
itchat.auto_login(enableCmdQR = 2, hotReload = True) #Login
Id = itchat.search_friends(name = "周宸宇")[0]['UserName']
t = threading.Thread(target=wechatreply, args=(Id,))
t.start()
GPIO.setmode(GPIO.BOARD)
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

while 1:
	knock_btn()
	face_key = "232d6ece9aad407c89067c63be83c3cf"
	CF.Key.set(face_key)
	personGroupId = "leiyiran"
#Try to take a photo for you
	print("please face the camera and hold still")
	os.system('aplay face_camera.wav')
	light(11,5,0.2)
	os.system('sudo raspistill -o face_recognition.jpg -w 640 -h 480')
	os.system('aplay kacha.wav')
	light_out(11)
	testImageFile = "face_recognition.jpg"
	faces = CF.face.detect(testImageFile)
	if len(faces) == 0:
		os.system('aplay noface.wav')
		print("Please let at least one person face the cemera!")
	else:
		times_count = 0
		for i in range(0,len(faces)):
			faceIds = [faces[i]['faceId']]
			res = CF.face.identify(faceIds, personGroupId)
			candidate = res[i]['candidates']
			if candidate == []:
				print("error!")
			else:
				confidence = candidate[i]['confidence']
				print("Confidence： " + str(confidence))
				if confidence >= 0.7:
					print("Accept!Welcome!")
					os.system('aplay welcome.wav')
					open_door()
					break
			times_count = times_count + 1

		if times_count == len(faces):
			os.system('aplay Denied.wav')
			print("Permission Denied!You are not authorized to open the door")
			send_picture("face_recognition.jpg",Id)
			send_message("This person is knocking the door!",Id)
			while 1:
				time.sleep(0.1)
				record_btn(Id)
				if GPIO.input(16) == GPIO.HIGH:
					break
		


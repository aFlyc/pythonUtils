#coding=utf-8
import os
import sys
#使用方法python compress.py minQuality-maxQuality(默认40-60) platform(默认wechatgame)
#eg:
#python compress.py 50-60 按照50-60的压缩质量压缩../build/wechatgame/下面的图片
#python compress.py 50-60 facebook 按照50-60的压缩质量压缩../build/facebook/下面的图片

PNGQUANT_PATH = './pngquant/'

if sys.platform == 'win32':
	PNGQUANT_PATH += 'windows/pngquant.exe '#windows平台尚未测试过
elif sys.platform == 'darwin':
	PNGQUANT_PATH += 'mac/pngquant '

SRC_FILE_PATH = '../build/'
OUTPUT_FILE_PATH = '../build/'
COMPRESS_TYPE_ARR = ['.png', '.jpg']
QUALITY = ' --quality='

def getFileSuffix(fileName):
	if not fileName:
		return ''
	suffix = os.path.splitext(fileName)[1]
	return suffix

def compressSingleImg(srcFilePath, outPutFilePath):
	print('start compress' + srcFilePath)
	os.system(PNGQUANT_PATH +  srcFilePath + ' -o ' + outPutFilePath + QUALITY + ' --skip-if-larger  --force')

def getFileFullPath(root, fileName):
	return root + '/' + fileName

def createDir(dir):
	if not os.path.exists(dir):
		os.makedirs(dir)

def getFileDir(path):
	return os.path.split(path)[0]

def compress():
	if not os.path.exists(SRC_FILE_PATH):
		print("invalid sources path:" + SRC_FILE_PATH)
		return
	print('start compress:')
	for root, dirs, files in os.walk(SRC_FILE_PATH):
		for fileName in files:
			suffix = getFileSuffix(fileName)
			if suffix in COMPRESS_TYPE_ARR:
				fileFullPath = getFileFullPath(root, fileName)
				outPutFileFullPath = fileFullPath.replace(SRC_FILE_PATH, OUTPUT_FILE_PATH)
				createDir(getFileDir(outPutFileFullPath))
				compressSingleImg(fileFullPath, outPutFileFullPath)

	print('finished compress')
	print('src file path:' + SRC_FILE_PATH)
	print('output file path:' + OUTPUT_FILE_PATH)

argvLen = len(sys.argv)
if argvLen == 1:
	SRC_FILE_PATH += 'wechatgame'
	OUTPUT_FILE_PATH += 'wechatgame'
	QUALITY += '40-60'
	compress()
elif argvLen == 2:
	SRC_FILE_PATH += 'wechatgame'
	OUTPUT_FILE_PATH += 'wechatgame'
	QUALITY += sys.argv[1]
	compress()
elif argvLen == 3:
	QUALITY += sys.argv[1]
	SRC_FILE_PATH += sys.argv[2]
	OUTPUT_FILE_PATH += sys.argv[2]
	compress()
else:
	print('invalid argv num, please check')

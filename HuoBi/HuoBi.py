#!/usr/bin/python
# -*- coding: UTF-8 -*- 
import sys
import os
from enum import Enum

from huobi.model.market import candlestick
from huobi_Python.build.lib.huobi.model.generic import symbol
from huobi.connection.websocket_req_client import WebSocketReqClient
import time
import datetime
from huobi.client.market import *
from huobi.constant import *
from huobi.utils import *
from huobi.client.generic import GenericClient
from huobi.model.market.candlestick_event import CandlestickEvent
from huobi.exception.huobi_api_exception import HuobiApiException


# os.system("$Env:http_proxy=\"http://127.0.0.1:7890\";$Env:https_proxy=\"http://127.0.0.1:7890\"")
# os.system("set http_proxy=http://127.0.0.1:1080")
# os.system("set https_proxy=http://127.0.0.1:1080")
class CheckType(Enum):
    ONE_HOUR = 1,
    FOUR_HOURS = 2,
    ONE_DAY = 3,
    ONE_WEEK = 4,
    ONE_MONTH = 5,

    FIVE_MINS = 10,
    TEN_MINS = 11,
    FIFTEEN_MINS = 12


SHOW_DEBUG_LOG = True
checkMA = False
onlyCheckUSDTSymbol = True
startTimeFromNow = 3600 * 24 * 0.5#检测时间跨度
limitPriceRate = 0.15#价格涨跌幅要小于这个限额
usdValueLimit = 1000#交易价值要大于这个限额
btcValueLimit = usdValueLimit / 35000
ethValueLimit = usdValueLimit / 2200
htValueLimit = usdValueLimit / 10
minVolueScale = 5
timeLimit = 0#最近n个k线不能超过MA200
candlestickName = "60min"
singleCandlestickInterval = 3600

checkType = CheckType.TEN_MINS
if checkType == CheckType.ONE_HOUR:
    candlestickName = "60min"
    singleCandlestickInterval = 3600
    startTimeFromNow = 3600 * 24 * 7
    limitPriceRate = 0.15#价格涨跌幅要小于这个限额
    usdValueLimit = 1000#交易价值要大于这个限额
    minVolueScale = 5
    btcValueLimit = usdValueLimit / 35000
    ethValueLimit = usdValueLimit / 2200
    htValueLimit = usdValueLimit / 10

elif checkType == CheckType.FOUR_HOURS:
    candlestickName = "4hour"
    singleCandlestickInterval = 3600 * 4
    startTimeFromNow = 3600 * 24 * 7
    limitPriceRate = 0.15#价格涨跌幅要小于这个限额
    usdValueLimit = 1000#交易价值要大于这个限额
    minVolueScale = 5
    btcValueLimit = usdValueLimit / 35000
    ethValueLimit = usdValueLimit / 2200
    htValueLimit = usdValueLimit / 10

elif checkType == CheckType.ONE_DAY:
    candlestickName = "1day"
    singleCandlestickInterval = 3600 * 24
    startTimeFromNow = 3600 * 24 * 30
    limitPriceRate = 0.15#价格涨跌幅要小于这个限额
    usdValueLimit = 1000#交易价值要大于这个限额
    minVolueScale = 5
    btcValueLimit = usdValueLimit / 35000
    ethValueLimit = usdValueLimit / 2200
    htValueLimit = usdValueLimit / 10

elif checkType == CheckType.FIVE_MINS:
    candlestickName = "5min"
    singleCandlestickInterval = 3600 * 24
    startTimeFromNow = 3600 * 24
    limitPriceRate = 0.05#价格涨跌幅要小于这个限额
    usdValueLimit = 10000#交易价值要大于这个限额
    minVolueScale = 15
    btcValueLimit = usdValueLimit / 35000
    ethValueLimit = usdValueLimit / 2200
    htValueLimit = usdValueLimit / 10

elif checkType == CheckType.TEN_MINS:
    candlestickName = "10min"
    singleCandlestickInterval = 3600 * 24
    startTimeFromNow = 3600 * 24
    limitPriceRate = 0.05#价格涨跌幅要小于这个限额
    usdValueLimit = 10000#交易价值要大于这个限额
    minVolueScale = 15
    btcValueLimit = usdValueLimit / 35000
    ethValueLimit = usdValueLimit / 2200
    htValueLimit = usdValueLimit / 10

allTargetSymbols = []
with open("TargetSymbols.txt", 'w+') as f:
    f.seek(0)
    f.truncate()

class SymbolSignalData:
    symbol = ""
    signalList = []

    def __init__(self, symbol, signalList):
        self.symbol = symbol
        self.signalList = signalList

class SingleSignal:
    volumeScale = 0
    candleStick = {}
    def __init__(self, volumeScale, candleStick):
        self.volumeScale = volumeScale
        self.candleStick = candleStick


targetSymbolList = []

list_obj = []
def getAllSymbols() -> str:
    generic_client = GenericClient()
    list_obj = generic_client.get_exchange_symbols()
    allSymbol = ""
    if len(list_obj):
        for idx, row in enumerate(list_obj):
            # LogInfo.output("------- number " + str(idx) + " -------")
            # row.print_object()
            allSymbol += "," + row.symbol
    allSymbol = allSymbol.replace(",", "", 1)
    return allSymbol


#获取指定时间段k线
def callback(candlestick_req: 'CandlestickReq'):
    candlestick_req.print_object()

# 时间戳转换成时间字符串
def getDateStrFromTimeStamp(timeStamp: float) -> str:
    time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timeStamp))
    return time_str

def getTradeValueLimit(channel: str) -> float:
    splitList = channel.split('.')
    symbol = splitList[1]
    limit = usdValueLimit
    if (symbol.endswith("btc")):
        limit = btcValueLimit
    elif symbol.endswith("eth"):
        limit = ethValueLimit
    elif symbol.endswith("ht"):
        limit = htValueLimit
    return limit

def checkCandlestick(candlestick_req: 'CandlestickReq', dataIdx: int) -> bool:
    if dataIdx < 0:
        return False
    ma200 = 0
    ma120 = 0
    ma30 = 0
    ma20 = 0
    count = 0
    
    checkData = candlestick_req.data[dataIdx]
    # if (time.localtime(checkData.id).tm_hour != 0):#跳过零点的涨幅
    #     return False
    priceChangeRate = abs((checkData.close - checkData.open) / checkData.open)
    while dataIdx >= 0:
        close = candlestick_req.data[dataIdx].close
        if (count < 200):
            ma200 += close
        if (count < 120):
            ma120 += close
        if (count < 30):
            ma30 += close
        if (count < 20):
            ma20 += close   
        count += 1
        dataIdx -= 1
    
    ma200 /= 200
    ma120 /= 120
    ma20 /= 20

    valueLimit = getTradeValueLimit(candlestick_req.rep)
    if checkMA and (ma120 >= ma200 or ma20 >= ma200):#均线要空头排列
        if SHOW_DEBUG_LOG:
            print (getDateStrFromTimeStamp(checkData.id) + "当前k线不为空头排列，不成立：MA200:" + str(ma200) + " MA120:" + str(ma120) + " MA20:" + str(ma20) + "\n") 
        return False
    # elif checkMA and (checkData.open >= ma200 or checkData.close >= ma200 or checkData.close < ma20):#k线要在ma200之下 ma20之上
    #     if SHOW_DEBUG_LOG:
    #         print (getDateStrFromTimeStamp(checkData.id) + "当前k线值高于MA200，不成立: MA200:" + str(ma200) + " MA120:" + str(ma120) + " MA20:" + str(ma20) + "\n")
    #         checkData.print_object()
    #     return False
    # elif  checkMA and ((checkData.close < checkData.open) or (checkData.low > ma20) or (checkData.close < ma20)):#k线要由下往上穿越MA20
    #     return False
    elif priceChangeRate > limitPriceRate:
        if SHOW_DEBUG_LOG:
            print (getDateStrFromTimeStamp(checkData.id) + "当前涨幅绝对值" + str(priceChangeRate * 100) + "% >" + str(limitPriceRate * 100) + "%,不成立")
            checkData.print_object()
        return False
    elif checkData.vol < valueLimit:
        if SHOW_DEBUG_LOG:
            print (getDateStrFromTimeStamp(checkData.id) + "当前交易额小于$" + str(valueLimit) + ",不成立")
            checkData.print_object()
    else:
        return True

# {
#     "id": 1489464480,
#     "amount": 0.0,
#     "count": 0,
#     "open": 7962.62,
#     "close": 7962.62,
#     "low": 7962.62,
#     "high": 7962.62,
#     "vol": 0.0
# }
def checkSymbol(candlestick_req: 'CandlestickReq'):
    idx = 0
    lastVolume = 0
    volumeScale = 0
    print ("处理:" + candlestick_req.rep)

    dataLen = len(candlestick_req.data)
    i = 0
    while (i < timeLimit and  i < dataLen):
        if not checkCandlestick(candlestick_req, dataLen - i - 1):
            return
        i += 1
    
    curTime = int(time.time())
    minTime = curTime - startTimeFromNow 
    rep = candlestick_req.rep 
    curSymbol = rep.split(".")[1]#交易对
    
    signalList = []
    for row in candlestick_req.data:
        #计算交易量
        if lastVolume > 0:
            volumeScale = row.amount / lastVolume
            if volumeScale >= minVolueScale and row.id > minTime and checkCandlestick(candlestick_req, idx):
                if SHOW_DEBUG_LOG:
                    volumeChangeSignal = getDateStrFromTimeStamp(row.id) + " 成立:\nvolume scale ->" + str(volumeScale) +  " value->" + str(row.vol) + "\n"
                    print(volumeChangeSignal)
                signalList.append(SingleSignal(volumeScale, row))
                
                
        idx += 1
        lastVolume = row.amount

    if onlyCheckUSDTSymbol and not curSymbol.endswith("usdt"):
        print ("跳过非USDT交易对")
        return
    elif len(signalList) > 0:
        signalList.sort(key=lambda x:x.volumeScale, reverse=True)
        allTargetSymbols.append(curSymbol)
        info = ""
        info += "#################Should pay attention:#################\n--------------" + curSymbol + "--------------:\n"
        for singleSignal in signalList:
            info += ">>>>>>>>\n"
            info += getDateStrFromTimeStamp(singleSignal.candleStick.id) 
            info += "\nVolumeScale:" + str(singleSignal.volumeScale) + "\n"
            candlestick = singleSignal.candleStick
            # info += "Id:" + str(candlestick.id) + "\n"
            # info += "High:" + str(candlestick.high) + "\n"
            # info += "Low:" + str(candlestick.low) + "\n"
            # info += "Open:" + str(candlestick.open) + "\n"
            # info += "Close:" + str(candlestick.close) + "\n"
            # info += "Count:" + str(candlestick.count) + "\n"
            # info += "Amount:" + str(candlestick.amount) + "\n"
            info += "Volume:" + str(candlestick.vol) + "\n"
            info += ">>>>>>>>\n"
        info +="#################\n\n"

        with open("TargetSymbols.txt", 'a+') as f:
            f.write(info)
    

def error(e: 'HuobiApiException'):
    print(e.error_code + e.error_message)

def checkAllSymbols():
    t = time.time()
    market_client = MarketClient()
    allSymbols = "bch3susdt,iosteth,tnbusdt,baleth,1inchusdt,cvntbtc,newusdt,ardrbtc,elfeth,kcasheth,eos3lusdt,irishusd,frontbtc,reefbtc,pondeth,hbarusdt,datbtc,engeth,blzbtc,icxeth,lxtusdt,bagsusdt,forht,mdxht,swftcusdt,maneth,mdsusdt,filbtc,ethusdc,flowbtc,ctsiusdt,bcxbtc,emusdt,bethusdt,dkaeth,bchusdt,scbtc,aaveusdt,aeusdt,akrobtc,yeebtc,bcveth,lskbtc,zlaeth,maskusdt,steembtc,nbsbtc,crousdt,triobtc,tosbtc,aacbtc,gofusdt,cvpusdt,elausdt,xchbtc,lunausdt,vethusd,etchusd,api3btc,xemusdt,atomusdt,enjeth,eos3susdt,dashhusd,sushibtc,neareth,mdxbtc,forbtc,chzeth,btteth,akroht,swrvusdt,pvtbtc,btc1susdt,xlmusdt,eth3susdt,rndreth,egcceth,ftieth,anteth,mcobtc,btmusdt,grsbtc,yfiusdt,bsv3susdt,woobtc,mkrbtc,utkbtc,yamusdt,geteth,usdthusd,axsbtc,balhusd,cvcoinbtc,stneth,trxbtc,chateth,dhtbtc,grtusdt,bandusdt,bt2btc,egtusdt,dgdeth,uuuusdt,rvnusdt,fildaeth,vidyusdt,polybtc,uniusdt,fisbtc,pvtht,cvcbtc,lbabtc,bnteth,bateth,caneth,aidoceth,wavesbtc,mtxbtc,dbceth,dgbbtc,chrusdt,bixeth,stptbtc,trbusdt,rdnbtc,nsurebtc,portalbtc,ugasbtc,ogousdt,gtcbtc,mlnbtc,vetusdt,mtxeth,yfiibtc,iotxusdt,waxpeth,gveeth,pearleth,kavabtc,linausdt,competh,vsysusdt,cmtusdt,apnusdt,nsureeth,loombtc,polsusdt,dbcbtc,uni2susdt,algousdt,zeneth,aidocbtc,raiusdt,zec3lusdt,htbtc,yfihusd,asteth,wtceth,getbtc,btseth,btttrx,waxpbtc,dockusdt,luneth,omghusd,dacbtc,fil3lusdt,stakeeth,snxbtc,ltcbtc,zecusdt,socusdt,jstusdt,lrceth,sspeth,dogehusd,xrpht,nanousdt,ctxcusdt,mkreth,hbcbtc,compbtc,cnnbtc,cmteth,injeth,linaeth,snxeth,zksusdt,covaeth,elahusd,chatbtc,adahusd,phaeth,arpaht,xtzbtc,ltcht,xmxbtc,sncbtc,actbtc,mxht,smtusdt,letbtc,mirbtc,pntbtc,ontusdt,paxusdt,dot2lusdt,itcusdt,gvebtc,ruffeth,hbcht,sklusdt,fsnht,eosusdt,massusdt,etneth,arpabtc,stptht,nhbtcusdt,crohusd,linkbtc,btchusd,dtabtc,wtcbtc,titaneth,rbtcbtc,meetbtc,jsteth,qtumhusd,nodeht,linkusdt,dtaeth,socbtc,kcashbtc,onebtc,lbaeth,chrht,xrtbtc,thetahusd,dashusdt,toseth,loomusdt,cvnteth,solusdt,manbtc,xmrbtc,fileth,etcusdt,ognusdt,edubtc,zlabtc,quneth,ftiusdt,venbtc,gxcbtc,xmxusdt,nknbtc,ucbtc,topusdt,sandusdt,ethbtc,titanbtc,paiusdt,xlmhusd,hitusdt,mdseth,bntbtc,batbtc,pcbtc,neobtc,wbtceth,insurusdt,xrpbtc,axseth,elaeth,renbtc,lolht,faireth,o3usdt,iostbtc,manaeth,irisusdt,seelebtc,hotbtc,kanusdt,sntusdt,ruffbtc,borusdt,mtabtc,topcbtc,dashbtc,paybtc,pearlusdt,ankrht,xmrusdt,canusdt,rlcusdt,boxbtc,datxbtc,link3lusdt,apneth,sbtcbtc,pondbtc,venusdt,knceth,paibtc,etcbtc,dothusd,lendeth,storjbtc,solbtc,nccbtc,creht,dot2susdt,adxbtc,dateth,xrpusdt,skleth,vsysht,injbtc,swftceth,algobtc,areth,bsvhusd,topbtc,renbtceth,crvbtc,icpusdt,btc3susdt,wxtusdt,hotusdt,dotbtc,mxcbtc,cruusdt,gtht,glmeth,atpbtc,dcrbtc,ttht,kanbtc,sceth,renusdt,o3btc,dcreth,hteth,rcccbtc,lendusdt,dgdbtc,onthusd,mdxusdt,zrxbtc,grseth,zechusd,ethusdt,btc3lusdt,borbtc,zec3susdt,ckbht,titanusdt,fttusdt,storjusdt,zrxeth,nknusdt,forthbtc,pvtusdt,sunbtc,bandbtc,dotusdt,dfbtc,cnnsusdt,wxtbtc,smteth,renhusd,mxcusdt,xrp3lusdt,abtusdt,abteth,dogeeth,topceth,ocnbtc,rccceth,dogeusdt,manausdt,ltchusd,yamv2btc,yambtc,ksmbtc,lambeth,iriseth,injusdt,atpusdt,boreth,trxeth,bixusdt,wbtcusdt,wanbtc,ugaseth,portaleth,insureth,egtbtc,aavehusd,dogebtc,soleth,kcashusdt,unibtc,icpbtc,yccbtc,crveth,hitbtc,yamv2eth,paxhusd,oneusdt,bandeth,abtbtc,xtzhusd,qunbtc,glmbtc,forthusdt,swftcbtc,fairbtc,raieth,axsusdt,gscbtc,fttbtc,renbtcbtc,akrohusd,nestht,xrtusdt,croht,sunusdt,gxcusdt,skmht,eoshusd,insurbtc,glmusdt,kncbtc,bcdbtc,pondusdt,unieth,crueth,yameth,irisbtc,lambbtc,veteth,ncceth,waneth,mtaeth,bhdusdt,hptbtc,api3eth,sandbtc,arusdt,mdsbtc,ocneth,hiveht,linkhusd,lendbtc,datxeth,elabtc,dfusdt,lunabtc,seeleusdt,rsrht,xmreth,swrvbtc,wbtcbtc,arbtc,manabtc,yamv2usdt,xtzusdt,mcousdt,reqeth,zkseth,hoteth,xembtc,kaneth,xrteth,uceth,snceth,soceth,qspeth,nanoeth,ekoeth,pceth,usdchusd,qasheth,ncasheth,snxusdt,maticeth,linabtc,paieth,buteth,cmtbtc,ctxceth,woousdt,yfibtc,hptusdt,hthusd,sspbtc,badgereth,docketh,trxusdt,omgbtc,kavahusd,nftusdt,zilhusd,nsureusdt,eosht,zrxusdt,npxseth,veneth,mtbtc,jstbtc,kmdeth,stptusdt,bch3lusdt,acteth,algoeth,mtht,kncusdt,mkrusdt,lambusdt,lbausdt,avaxbtc,qtumusdt,thetausdt,bchht,waxpusdt,nasbtc,ringeth,dtausdt,etnbtc,rcnbtc,xrphusd,steemusdt,nbsusdt,vetbtc,cnnsht,bhdht,crubtc,bhdbtc,smtbtc,filusdt,lxtbtc,linketh,sushihusd,tnbbtc,reefusdt,apnbtc,srneth,blzusdt,rdneth,itceth,frontusdt,ksmusdt,hiteth,aebtc,xrp3susdt,ltc3lusdt,mexbtc,raibtc,zjlteth,bchbtc,onteth,polseth,ocnusdt,gxceth,ruffusdt,atombtc,pundixbtc,seeleeth,cnnsbtc,gsceth,cdcbtc,waveseth,appcbtc,ycceth,ltcusdt,iotxeth,latusdt,ckbusdt,tnteth,gofbtc,nexousdt,mtlbtc,bixbtc,cvpbtc,api3usdt,nulseth,xchusdt,zenbtc,hbcusdt,ognht,wnxmeth,cvcoineth,btmeth,crvusdt,wtcusdt,pnteth,rvnbtc,btsbtc,uuueth,forusdt,embtc,sushiusdt,daceth,rsrhusd,newht,pearlbtc,btmbtc,gnxeth,powreth,idteth,adxeth,ognbtc,rvnht,mtausdt,bttusdt,vidybtc,propybtc,compusdt,covabtc,arpausdt,egccbtc,uuubtc,antbtc,dhteth,newbtc,canbtc,fortheth,gaseth,meeteth,suneth,lhbusdt,mireth,1inchbtc,polyeth,leteth,xlmeth,dcrusdt,gtceth,mirusdt,massbtc,ethhusd,sntbtc,fisusdt,tusdhusd,bsvusdt,eosbtc,tntbtc,yfiiusdt,ltc3susdt,lsketh,dkabtc,hbareth,cdceth,nesthusd,htusdt,link3susdt,aeeth,loometh,sklbtc,cvceth,reneth,gtusdt,gofeth,cvpeth,xmxeth,trbbtc,aavebtc,mdxeth,wavesusdt,hbarbtc,utketh,polsbtc,payeth,iotaeth,bt1btc,ftibtc,stakebtc,kavausdt,vidyht,boxeth,ogobtc,neousdt,scusdt,akrousdt,trioeth,xlmbtc,mlnusdt,firoeth,bntusdt,batusdt,bftbtc,edueth,1incheth,knchusd,flowusdt,iostusdt,steemeth,ogoht,bsv3lusdt,propyeth,yeeeth,astbtc,chzusdt,nearusdt,reefeth,rsrbtc,nuusdt,ttusdt,bcvbtc,maticbtc,nknht,nanobtc,qspbtc,floweth,stnbtc,mxbtc,bchausdt,itcbtc,evxeth,enjusdt,qashbtc,fsnbtc,lolbtc,daihusd,yfieth,blzeth,ctxcbtc,icxbtc,ontbtc,omgeth,gtbtc,aaceth,antusdt,rndrbtc,balbtc,actusdt,zecbtc,lxteth,atometh,badgerusdt,fildabtc,stakeusdt,npxsbtc,zksbtc,swrveth,kmdbtc,atpht,trxhusd,elfbtc,appceth,ardreth,oneht,iotxbtc,18ceth,nodebtc,ncashbtc,fronteth,bandhusd,rcneth,wiccusdt,chrbtc,ankrusdt,cnneth,xtzeth,dkausdt,iotausdt,uipbtc,butbtc,letusdt,lrcbtc,mexeth,ekobtc,ksmhusd,astusdt,snxhusd,zjltbtc,betheth,zenusdt,vsysbtc,usdcusdt,osteth,firobtc,dfht,tnbeth,mcoeth,mxusdt,btsusdt,fsnusdt,balusdt,bfteth,topht,unihusd,bchabtc,icxusdt,thetaeth,engbtc,iostht,chzbtc,nearbtc,rsrusdt,ringbtc,crvhusd,mlneth,badgerbtc,ttbtc,bttbtc,aaveeth,elfusdt,bchhusd,btmhusd,hcusdt,phabtc,lunbtc,iotabtc,nhbtceth,nodeusdt,auctioneth,masseth,dashht,ankrbtc,kcashht,mkrhusd,nubtc,zilusdt,crebtc,firousdt,nasusdt,emht,avaxeth,yfiieth,eoseth,dockbtc,uipusdt,iiceth,reqbtc,mteth,bsvbtc,dacusdt,trbeth,zrxhusd,nftht,xvgeth,lrcusdt,powrbtc,yeeusdt,boringusdt,adausdt,kavaeth,phxbtc,gasbtc,hiveusdt,valueusdt,shebtc,ringusdt,wxtht,lambht,salteth,algohusd,iicbtc,mtnbtc,botusdt,wiccbtc,stkbtc,ksmht,nesteth,oxtusdt,muskbtc,srnbtc,iosthusd,qtumeth,nestusdt,lymbtc,wicceth,zilbtc,oxteth,grtbtc,bkbteth,creusdt,rndrusdt,acheth,latbtc,umaeth,umausdt,dhtusdt,mtneth,wpreth,wnxmbtc,nulsbtc,ekteth,musketh,saltbtc,eth3lusdt,gnxbtc,sheeth,valueeth,idtbtc,achusdt,etcht,phausdt,skmusdt,dgbeth,hcbtc,utkusdt,sushieth,csprbtc,filhusd,rtebtc,ckbbtc,cvcusdt,ektusdt,neohusd,adaeth,btgbtc,nexobtc,shibusdt,btcusdt,uni2lusdt,wprbtc,fiseth,bifibtc,skmbtc,auctionbtc,crobtc,achbtc,botbtc,lunaht,valuebtc,18cbtc,xvgbtc,nulsusdt,hptht,lymeth,maticusdt,zileth,boringeth,gnxusdt,btcusdc,stnusdt,boringbtc,boteth,umabtc,omgusdt,grteth,pundixeth,bkbtbtc,egtht,sandht,oxtbtc,evxbtc,aacusdt,uipeth,fildausdt,avaxusdt,hceth,hivebtc,naseth,nexoeth,wooeth,rteeth,lolusdt,stketh,adabtc,nestbtc,fttht,auctionusdt,fil3susdt,enjbtc,ostbtc,wnxmusdt,thetabtc,eth1susdt,ektbtc,qtumbtc,daiusdt,csprusdt"
    # allSymbols = getAllSymbols()
    # print(allSymbols)

    symbolsList = allSymbols.split(',')
    count = 0
    symbolLen = len(symbolsList)
    for symbol in symbolsList:
        time.sleep(0.01)
        count += 1
        if onlyCheckUSDTSymbol:
            if symbol.endswith("usdt"):
                market_client.req_candlestick(symbol, candlestickName, checkSymbol, from_ts_second=int(t) - singleCandlestickInterval * 800, end_ts_second=int(t))
        else:
            market_client.req_candlestick(symbol, candlestickName, checkSymbol, from_ts_second=int(t) - singleCandlestickInterval * 800, end_ts_second=int(t))
        # if (symbolLen == count):
        #     time.sleep(0.5)
        #     with open("TargetSymbols.txt", 'a+') as f:
        #         info = "\nTargetsSymbol:\n"
        #         for symbol in allTargetSymbols:
        #             info += symbol + ","
        #         content = f.read()        
        #         f.seek(0, 0)
        #         f.write(info)
        #         f.close()

checkAllSymbols()
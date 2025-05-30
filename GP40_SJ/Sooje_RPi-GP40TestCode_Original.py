#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2020-10-23: SPI CS端子をGPIO制御方式へ変更

import sys,os
import time

import spidev           #SPI制御用
import RPi.GPIO as GPIO #GPIO制御用

from datetime import datetime, timedelta

import csv
import traceback


# グローバル変数
v_rstr = ["±10V","±5V","±2.5V","±1.25V","±0.5V","0-10V","0-5V","0-2.5V","0-1.25V","0-20mA","NONE"]   # レンジ文字列
v_chn  = [      0,     1,       2,        3,      11,      5,     6,       7,       15,       6,     0]   # レンジ選択レジスタへ書き込む値のテーブル
v_chu  = [  0x800, 0x800,   0x800,    0x800,   0x800,  0x000, 0x000,   0x000,    0x000,   0x000, 0x000]   # 実値変換減算値 0x800:バイポーラ 0x000:ユニポーラ
v_chm  = [   5.00,  2.50,    1.25,    0.625,  0.3125,   2.50,  1.25,   0.625,   0.3125,    5.00,   0.0]   # 実値変換乗算値 1LSB[mV](/[uA])
v_chr  = [0,0,0,0,0,0,0,0]         # ch0-7の入力レンジ初期値
v_adach = 0                        # ADアラーム発生ch bit0-7=ch0-7 bit8=DIN
v_adadt = 0                        # デジタル入力検知時のADC ch0値
#ADCS = 8                           # AD SPI CS端子のGPIO番号 8

# RPi-GP40初期設定
def init_GP40():
    GPIO.setmode(GPIO.BCM)                                # Use Broadcom pin numbering
    GPIO.setwarnings(False)
    GPIO.setup(ADCS, GPIO.OUT, initial=GPIO.HIGH)         # ADCS はGPIO端子として制御する
    GPIO.setup(27,   GPIO.OUT, initial=GPIO.HIGH )        # RPi-GP40絶縁電源ON
    GPIO.setup(DOUT, GPIO.OUT, initial=GPIO.LOW )         # DOUT端子出力設定 LOW (=OFF:オープン)
    GPIO.setup(DIN,  GPIO.IN,  pull_up_down=GPIO.PUD_OFF) # DIN端子入力設定
    time.sleep(0.5)                                       # 電源安定待ち

# ADCとのSPIデータ転送
# 2020-05-27以降のraspi-osで、SPI CS端子に余分な'L'パルスが発生する現象の対策としてGPIO制御方式へ変更(2020-10-23)
def xfer_spiadc( wd ):
    GPIO.output(ADCS, 0)         # SPI CS0='L' GPIO端子として制御する
    rd = spi.xfer(wd)
    GPIO.output(ADCS, 1)         # SPI CS0='H'
    return rd

# 指定chのレンジ選択レジスタ値を設定
def set_adrange(ch, r):
    wdat = [((5+ch)<<1)|1, r, 0x00, 0x00]     # chの入力レンジ設定
    rdat = xfer_spiadc(wdat)

# 指定chのレンジ選択レジスタ値を取得
def get_adrange(ch):
    wdat = [((5+ch)<<1)|0, 0x00, 0x00, 0x00]  # chの入力レンジ取得
    rdat = xfer_spiadc(wdat)
    return rdat[2]

# 指定chのAD変換データ取得
def get_addata(ch):
    wdat = [0xc0+(ch<<2), 0x00, 0x00, 0x00]   # ch'ch'をAD変換する
    rdat = xfer_spiadc(wdat)                  # ch指定
#   time.sleep(0.1)
    rdat = xfer_spiadc(wdat)                  # ADデータ取得
    adat = (rdat[2]<<4)+(rdat[3]>>4)          # AD変換値
    return adat

# ch0-7のAD変換実行と結果表示
def print_adc(v_intv):                        # intv:表示間隔[sec] cnt:表示回数[回]
    global adach
    #for i in range(cnt):                      # 表示回数繰り返し
    
    v_array = []
    while(True) :
        v_adat = []; v_volt = [];
        for adc in range(8):                  # ch0-7
            if( v_chr[adc]>9 ):                 # 無効chなら、
                print("%8s ch%d:        [---]" % 
                    (v_rstr[v_chr[adc]], adc) )   # AD変換なし
            else:                             # 有効chなら、
                adat = get_addata(adc)        # ch'adc'をAD変換する
                #volt = (adat-chu[chr[adc]])*chm[chr[adc]]/1000  # 入力レンジでの実値算出 = (AD変換値-減算値)x乗算値
                volt = (adat-v_chu[v_chr[adc]])*v_chm[v_chr[adc]]
                #print("%8s ch%d:%8.4f[%03X]" % (rstr[chr[adc]], adc, volt, adat) )         # 結果表示
                v_adat.append(adat)
                v_volt.append(volt)
        print(f'[{datetime.now()}] {[f"{x:.1f}" for x in v_volt]}(mV), ADAT : {v_adat}')
        v_array.append( [datetime.now()] + v_volt )
        
        if len(v_array) > 30 :
            with open( os.path.join(v_abs_path, f"{datetime.now().strftime('%Y%m%d_%H0000')}_adc.csv"), "a+" ) as wf :
                csv.writer(wf).writerows(v_array)
            v_array = []; #init
        
        time.sleep(v_intv)
    
    print("")

##########################################################################################################################################

v_abs_path = r'/home/pi/Documents/spiadc'

def get_arg(index) :
    try               : sys.argv[index]
    except IndexError : return ''
    else              : return sys.argv[index]
    
# main
if __name__ == "__main__":
    global ADCS # 8 : (CH01~08), 7 : (CH09~16)
    if get_arg(1) == '' or int(get_arg(1)) : ADCS = 8
    else : ADCS = 7
    
    try:
        v_chr = [1]*8
        v_interval = 0.1
        
        # RaspberryPi SPI機能設定
        spi  = spidev.SpiDev()      # RPi-GP40はSPIを使用
        spi.open(0, 0)              #  SPI0, CEN0 でオープン
        spi.no_cs = True            #  CSはspidevではなくGPIOとして制御する Ra
        spi.mode = 1                #  SPIクロック設定 CPOL=0(正論理), CPHA=1(H->Lでデータ取り込み)
        spi.max_speed_hz = 10000000 #  SPIクロック最大周波数(17MHz指定)
                                    #   ただし、2018年4月時点のカーネル仕樣では、指定値より実周波数が低くなる
                                    #   17MHz→10.5MHz, 10MHz→6.2MHz, 8MHz→5MHz, 28MHz→15.6MHz
        DOUT = 12                   # デジタル出力 GPIO12(JP8:Default) / GPIO14(JP7)
        DIN  = 13                   # デジタル入力 GPIO13(JP6:Default) / GPIO15(JP5)
        
        # RPi-GP40初期設定
        init_GP40()

        # 入力レンジ設定
        for adc in range(8):
            if( v_chr[adc]<=9 ):    # 有効chなら、
                set_adrange(adc, v_chn[v_chr[adc]])     # ch'c'の入力レンジ設定

        # 引数による直接実行形式
        print_adc(v_interval)       # interval間隔でcnt回AD変換値表示
        raise GTE

    except GTE :
        pass
    # 例外処理
    except KeyboardInterrupt:       # CTRL-C キーが押されたら、
        print( "Keyboard Interrupt !!" )    # 中断
    except Exception as ex:               # その他の例外発生時
        print('에러발생[__main__] : {0}\n{1}'.format( ex, ''.join(traceback.TracebackException.from_exception(ex).format()) ));
    
    finally : 
        GPIO.output(27, False)          # RPi-GP40の絶縁電源OFF
        GPIO.cleanup()
        sys.exit()
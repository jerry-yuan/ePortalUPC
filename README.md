#中国石油大学(华东) 网络认证系统Python接口
##一、适用范围
2017年2月，我校从之前城市热点认证系统（Dr.COM）更换为锐捷ePortal认证系统，导致之前中国石油大学（华东）[Linux及自由软件协会](https://github.com/upclinux)（会长洋神）开发的[DrUPC](https://github.com/upclinux/DrUPC)失效。
##二、依赖关系
本项目使用Python 3.7开发，依赖于Python3的以下类库：
```
hashlib         实现验证码识别中的MD5计算
http.cookiejar  Cookie管理
json            解析JSON
urllib          HTTP请求
re              正则表达式相关
os              系统相关
```
##三、使用方法及API介绍
###1、整体介绍
本项目实现了基本的登录、注销、验证码识别及当前已登录用户信息获取等功能，核心类为EPortalAdapter，其主要用于与服务器进行通信。
###2、使用方法
当前仅仅开发了一套类接口，尚未开发面向shell的控制台程序或者网络监控模块,日后将逐步完善相关接口.

使用时需要根据API列表选择需要的接口进行Python程序的开发。
###3、类列表及API
####① `EPortalAdapter`
* `getValidCode()`
从服务器自动下载一个二维码图片,并将其识别成为以字符串表示的识别结果
* `getPageInfo(force=False)`
从服务器加载登录页面的一些信息,包括了可用的接入商以及公告等信息
* `getAvaliableISP()`
获取可用接入商列表.
* `login(username,password,ISP='default')`
登录网络认证系统.
* `logout()`
登出当前网号.
* `getCurrentUserInfo(showRaw=False)`
获取当前已登录网号的信息.
##四、示例代码
###1、检查网号并在网号被强制注销后自动登录
```
from EPortalAdapter import *

ePortal=EPortalAdapter()
username='1401010101'
password='123456'
isp='default'
if __name__ == '__main__':
    #ePortal.logout()
    try:
        print("查询当前用户信息...\t")
        userInfo=ePortal.getCurrentUserInfo()
        print("已登录为{}".format(userInfo['userName']))
    except UnLoginException as e:
        print("当前未登录")
        print("尝试使用{}登录...\t".format(username))
        try:
            ePortal.login(username,password,isp)
            print("登录成功!")
            userInfo=ePortal.getCurrentUserInfo()
            print("已登录为{}".format(userInfo['userName']))
        except LoginFailed as e:
            print(e)
    except Exception as e:
        print(e)
```
###2、未完待续
##五、鸣谢
感谢中国石油大学（华东）计算机与通信工程学院大数据实验室提供的需求。


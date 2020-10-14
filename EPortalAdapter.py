import hashlib
import http.cookiejar
import json
import logging
import os
import re
import urllib.parse
import urllib.request

from HTTPRedirectHandler import HTTPRedirectHandler


class UndefinedISP(Exception):
    def __init__(self, srv):
        self.srv = str(srv)

    def __str__(self):
        return "无法识别的ISP:{}".format(self.srv)


class UnLoginException(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "用户未登录"


class LoginFailed(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return "登录失败:{}".format(self.reason)


class UnExpectedStatusCode(Exception):
    def __init__(self, code, expected, addition=None):
        self.code = code
        self.expected = expected
        self.addition = addition

    def __str__(self):
        return "意外的HTTP响应码:{self.code}(期待{self.expected}):{self.addition}".format(self=self)


class ValidCodeRecognizeFailed(Exception):
    def __init__(self, reason, md5):
        self.reason = reason
        self.md5 = md5

    def __str__(self):
        return "识别验证码失败:{}:{}".format(self.reason, self.md5)


class QueryStringNotFound(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return "获取QueryString失败:{}".format(self.reason)


class LogoutFailed(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return "登出失败:{}".format(self.reason)


class EPortalAdapter:
    def __init__(self):
        self.validCodeDictFile = "./validCode.json"
        self.params = {
            "server": '121.251.251.207',
            "schema": 'http'
        }
        self.cookie = http.cookiejar.CookieJar()
        self.detectNetworkUrl = "http://www.upc.edu.cn"
        self.homePageUrl = "http://www.upc.edu.cn"
        self.redirectUrl = "{params[schema]}://{params[server]}/eportal/redirectortosuccess.jsp"
        self.interfaceUrl = "{params[schema]}://{params[server]}/eportal/InterFace.do?method={method}"
        self.validCodeUrl = "{params[schema]}://{params[server]}/eportal/validcode"
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie),
                                                  HTTPRedirectHandler())
        self.userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36"
        self.opener.addheaders = [
            ("Accept", "*/*"),
            ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
            ("Cache-Control", "no-cache"),
            ("Connection", "keep-alive")
        ]
        self.validCodeMap = None
        self.queryString = None
        self.pageInfo = None
        self.logger = logging.getLogger("ePortalAdapter")
        self.detectNetwork()

    # 向认证接口发送GET请求
    def _get(self, method):
        url = self.interfaceUrl.format(params=self.params, method=method)
        request = urllib.request.Request(
            url=url,
            headers={"User-Agent": self.userAgent}
        )
        self.logger.debug("[GET]{}".format(url))
        return self.opener.open(request)

    # 向认证接口发送POST请求
    def _post(self, method, data):
        url = self.interfaceUrl.format(params=self.params, method=method)
        self.logger.debug("[POST]{}".format(url))
        request = urllib.request.Request(
            url=url,
            data=urllib.parse.urlencode(data).encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": self.userAgent
            }
        )
        return self.opener.open(request)

    def detectNetwork(self):
        self.logger.info("[DetectNetwork]正在探测网络结构")
        try:
            request = urllib.request.Request(
                url=self.detectNetworkUrl,
                headers={"User-Agent": self.userAgent}
            )
            self.opener.open(request)
            raise UnExpectedStatusCode(200, 302, "探测网络环境失败")
        except urllib.request.HTTPError as e:
            if e.code != 302:
                raise UnExpectedStatusCode(e.code, 302, "探测网络环境失败")
            urlParsed = urllib.parse.urlparse(e.headers['location'])
            self.logger.info(
                "[DetectNetwork]认证服务器地址:{}".format(urlParsed.netloc))
            self.params['server'] = urlParsed.netloc
            self.params['scheme'] = urlParsed.scheme

    # 获取QueryString
    def getQueryString(self, force=False):
        # QueryString 缓存
        if not force and self.queryString is not None:
            self.logger.debug("[QueryString]使用缓存")
            return self.queryString
        # 检测网络状态
        try:
            request = urllib.request.Request(
                url=self.redirectUrl.format(params=self.params),
                headers={"User-Agent": self.userAgent}
            )
            self.opener.open(request)
        except urllib.request.HTTPError as e:
            urlParsed = urllib.parse.urlparse(e.headers['location'])
            if urlParsed.path == '/eportal/./success.jsp':
                raise QueryStringNotFound("可能网络正常")
        # 尝试获取QueryString
        try:
            request = urllib.request.Request(
                url=self.homePageUrl,
                headers={"User-Agent": self.userAgent}
            )
            scripts = self.opener.open(request).read()
            if type(scripts) == bytes:
                scripts = scripts.decode("utf-8")
            queryStrings = re.findall(
                r"http://121.251.251.217/eportal/index.jsp\?(.+?)", scripts)
            if len(queryStrings) < 1:
                raise QueryStringNotFound("可能网络正常")
            self.queryString = queryStrings
        except urllib.request.HTTPError as e:
            if e.code != 302:
                raise UnExpectedStatusCode(e.code, 302, "获取QueryString失败")
            location = e.headers['location']
            queryStrings = location.split("?")
            if len(queryStrings) < 2:
                raise QueryStringNotFound("Location格式有误:{}".format(location))
            self.queryString = queryStrings[1]
        except Exception as e:
            raise QueryStringNotFound(e.__str__())
        return self.queryString

    # 获取并识别一个验证码
    def getValidCode(self):
        validCode = '----'
        try:
            self.logger.debug("[验证码]尝试下载验证码图片.")
            response = self.opener.open(
                self.validCodeUrl.format(params=self.params))
            imgData = response.read()
            self.logger.debug("[验证码]图片大小为{}B".format(len(imgData)))
            imgMd5 = hashlib.md5(imgData).hexdigest()
            self.logger.debug("[验证码]MD5:{}".format(imgMd5))
            validCode = self.checkValidCode(imgMd5)
            self.logger.debug("[验证码]识别结果:{}".format(validCode))
        except urllib.request.HTTPError as e:
            raise UnExpectedStatusCode(e.code, 200, "下载验证码图片失败")
        return validCode

    # 根据md5值识别验证码
    def checkValidCode(self, md5):
        if self.validCodeMap == None:
            if not os.path.exists(self.validCodeDictFile):
                raise ValidCodeRecognizeFailed(
                    "验证码字典丢失,请确保{}的存在".format(self.validCodeDictFile), md5)
            with open(self.validCodeDictFile) as fi:
                self.validCodeMap = json.load(fi)

        if not md5 in self.validCodeMap.keys():
            raise ValidCodeRecognizeFailed("未收录的验证码", md5)
        return self.validCodeMap[md5]

    # 获取PageInfo
    def getPageInfo(self, force=False):
        if not force and self.pageInfo is not None:
            self.logger.debug("[PageInfo]采用缓存")
            return self.pageInfo
        response = self._post(
            "pageInfo", {"queryString": self.getQueryString()})
        self.pageInfo = json.load(response)
        return self.pageInfo

    # 登录网号
    def login(self, username, password, ISP="default"):
        if not ISP in self.getAvaliableISP():
            raise UndefinedISP(ISP)
        # 判断是否需要验证码
        pageInfo = self.getPageInfo()
        validCode = "" if not pageInfo['validCodeUrl'].strip(
        ) else self.getValidCode()
        try:
            response = self._post("login", {
                "operatorPwd": "",
                "operatorUserId": "",
                "password": password,
                "queryString": self.getQueryString(),
                "service": ISP,
                "userId": username,
                "validcode": validCode
            })
            result = json.load(response)
            if result["result"] == 'fail':
                self.pageInfo['validCodeUrl'] = result["validCodeUrl"]
                raise LoginFailed(result['message'])
        except urllib.request.HTTPError as e:
            raise LoginFailed(e)

    # 登出
    def logout(self, userIndex=None):
        try:
            if userIndex is None:
                userIndex = self.getCurrentUserInfo()['userIndex']
            result = json.load(self._post("logout", {"userIndex": userIndex}))
            if result['result'] == 'fail':
                raise LogoutFailed(result['message'])
        except urllib.request.HTTPError as e:
            raise LogoutFailed(e)
        except UnLoginException as e:
            raise LogoutFailed(e)
        return True

    # 获取当前用户状态
    def getCurrentUserInfo(self, showRaw=False):
        userInfo = None
        try:
            response = self._post("getOnlineUserInfo", {"userIndex": ""})
            userInfo = json.load(response)
            # 检查状态
            if userInfo['result'] == 'wait':
                return self.getCurrentUserInfo()
            elif userInfo['result'] == 'fail':
                raise UnLoginException()
            # 删掉没必要的数据
            if not showRaw:
                drops = ['announcement', 'ballInfo', 'message', 'notify', 'offlineurl', 'pcClientUrl', 'portalUrl',
                         'redirectUrl', 'selfUrl', 'successUrl', 'userUrl', 'utrustUrl', 'welcomeTip']
                for i in drops:
                    del userInfo[i]
                # 处理一下servicesList
                userInfo['serviceList'] = re.findall(
                    r'selectService\("(.+?)",', userInfo["serviceList"])
        except urllib.request.HTTPError as e:
            raise UnExpectedStatusCode(e.code, 200, "拉取当前用户信息失败")
        return userInfo

    # 获取可用的ISP
    def getAvaliableISP(self):
        try:
            pageInfo = self.getPageInfo()
            return list(pageInfo['service'].keys())
        except QueryStringNotFound:
            userInfo = self.getCurrentUserInfo()
            return list(userInfo['serviceList'])

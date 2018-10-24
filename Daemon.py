from EPortalAdapter import *
import time
import logging
import os
import argparse

ePortal = EPortalAdapter()

if __name__ == '__main__':
    # 切分参数
    parser = argparse.ArgumentParser()
    help = "启用全部调试输出"
    parser.add_argument("-v", "--verbose", default=os.getenv("EPORTAL_DEBUG", "False").lower() =="true", action="store_true",
                        help=help)
    help = "自动登录时使用的用户名,默认值为环境变量中EPORTAL_USERNAME的值"
    parser.add_argument("-u", "--username", default=os.getenv("EPORTAL_USERNAME", None), help=help)
    help = "自动登录时使用的密码,默认值为环境变量中EPORTAL_PASSWORD的值"
    parser.add_argument("-p", "--password", default=os.getenv("EPORTAL_PASSWORD", None), help=help)
    help = "自动登录时使用的运营商,默认值为default,可用EPORTAL_SERVICE覆盖"
    parser.add_argument("-s", "--service", default=os.getenv("EPORTAL_SERVICE", "default"), help=help)
    help = "网络状态检查间隔,默认600秒(10分钟),可用EPORTAL_INTERVAL覆盖"
    parser.add_argument("-i", "--interval", default=int(os.getenv("EPORTAL_INTERVAL", 600)), type=int, help=help)
    help = "失败自动重试次数,默认5次,可用EPORTAL_AUTORETRY覆盖"
    parser.add_argument("-r", "--retry-times", default=int(os.getenv("EPORTAL_AUTORETRY", 5)), type=int, help=help)
    help = "失败自动重试间隔,默认60秒,可用EPORTAL_AUTORETRY_INTERVAL覆盖"
    parser.add_argument("--retry-interval", default=int(os.getenv("EPORTAL_AUTORETRY_INTERVAL", 60)), type=int,
                        help=help)

    args = parser.parse_args()
    # 设置logging输出设置
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG if args.verbose else logging.INFO
    )
    # 检查参数
    if args.username is None:
        logging.error("未指定登录使用的用户名,请使用-u,--user或者EPORTAL_USERNAME指定!")
        exit(-1)
    if args.password is None:
        logging.error("未指定登录使用的密码,请使用-p,--password或者EPORTAL_PASSWORD指定!")
        exit(-1)
    if args.service not in ePortal.getAvaliableISP():
        logging.error("无法识别的服务提供商[{}],当前仅可用{}".format(args.service, ",".join(ePortal.getAvaliableISP())))
        exit(-1)
    if args.interval < 1:
        logging.error("时间间隔格式错误.")
        exit(-1)
    # debug
    logging.debug("程序启动")
    logging.debug("自动登录用户名:{}".format(args.username))
    logging.debug("自动登录密码:{}".format(args.password))
    logging.debug("自动登录ISP:{}".format(args.service))
    logging.debug("扫描间隔:{}秒".format(args.interval))
    logging.debug("最大失败重试次数:{}次".format(args.retry_times))
    logging.debug("扫描间隔:{}秒".format(args.retry_interval))
    # 一些信息
    if args.retry_times < 1:
        logging.warning("登录失败后将不自动重试!")
    if args.retry_times > 0 and args.retry_interval < 0:
        logging.info("登录失败后将立即重试.")
        args.retry_interval = 0
    # 开始尝试
    retryTimes = 0
    try:
        while True:
            try:
                if retryTimes > 0:
                    logging.info("尝试第{}次重试登录.".format(retryTimes))
                else:
                    logging.info("开始检查登录状态.")
                userInfo = ePortal.getCurrentUserInfo()
                logging.info("当前已登录为{}:{}".format(userInfo['userId'], userInfo['userName']))
                logging.info("网络状态正常,等待{}秒后刷新状态".format(args.interval))
                retryTimes=0
                time.sleep(args.interval)
            except UnLoginException as e:
                logging.warning("当前未登录任何网号!")
                logging.info("尝试使用{}登录...\t".format(args.username))
                try:
                    ePortal.login(args.username, args.password, args.service)
                    logging.info("登录成功.")
                    userInfo = ePortal.getCurrentUserInfo()
                    logging.info("当前已登录为{}:{}".format(userInfo['userId'], userInfo['userName']))
                except LoginFailed as e:
                    logging.error("登录失败:{}".format(e.reason))
                    # 重试次数大于0时候安排重试
                    if args.retry_times > 0:
                        if retryTimes > args.retry_times:  # 如果已经重试的次数大于等于设定的重试次数,则不再重试
                            logging.error("重试失败超过{}次,不再重试.".format(args.retry_times))
                            time.sleep(args.interval)
                            retryTimes = 0
                        else:
                            retryTimes += 1
                            if args.retry_interval > 0:
                                logging.info("等待{}秒进行第{}次重试登录.".format(args.retry_interval, retryTimes))
                                time.sleep(args.retry_interval)
    except KeyboardInterrupt:
        logging.info("检测到Ctrl+C,程序退出")
        quit(0)

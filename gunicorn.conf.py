accesslog = '-'
access_log_format = '%(t)s [%({x-forwarded-for}i)s %(M)sms] "%(m)s %(U)s?%(q)s" %(s)s %(b)s'
preload_app = True
timeout = 60
bind = '0.0.0.0:8889'
workers = 1
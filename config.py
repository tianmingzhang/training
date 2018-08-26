import pymongo

#flask-session配置
SECRET_KEY = '\x0e6\xcd#$\x985\xe9J\xdb\xc4wZ\xde\x82\xdd\xc0\xfd$\xf1/\x83\x9c\x08'
SESSION_TYPE = 'mongodb'  # session类型为mongodb
SESSION_MONGODB_DB = 'Todo'
SESSION_MONGODB_COLLECT = 'session'
SESSION_PERMANENT = True  # 如果设置为True，则关闭浏览器session就失效。
SESSION_USE_SIGNER = False  # 是否对发送到浏览器上session的cookie值进行加密
SESSION_KEY_PREFIX = 'session:'  # 保存到session中的值的前缀
SESSION_MONGODB = pymongo.MongoClient()


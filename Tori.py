from flask import Flask,session
from flask import render_template
from datetime import datetime,timedelta,timezone
from flask_pymongo import PyMongo
from collections import Iterable
from flask import jsonify
import itertools
import functools
from flask import request
from functools import wraps
from flask_session import Session
from bson.objectid import ObjectId
import pymongo
import time

app = Flask(__name__)
app.config['MONGO_HOST'] = '127.0.0.1'
app.config['MONGO_PORT'] = 27017
app.config['MONGO_DBNAME'] = 'Tori'
mongo = PyMongo(app, config_prefix='MONGO')

#flask-session配置
app.secret_key = '\x0e6\xcd#$\x985\xe9J\xdb\xc4wZ\xde\x82\xdd\xc0\xfd$\xf1/\x83\x9c\x08'
app.config['SESSION_TYPE'] = 'mongodb'  # session类型为mongodb

app.config['SESSION_MONGODB'] = pymongo.MongoClient()
app.config['SESSION_MONGODB_DB'] = 'Tori'
app.config['SESSION_MONGODB_COLLECT'] = 'session'

app.config['SESSION_PERMANENT'] = True  # 如果设置为True，则关闭浏览器session就失效。
app.config['SESSION_USE_SIGNER'] = False  # 是否对发送到浏览器上session的cookie值进行加密
app.config['SESSION_KEY_PREFIX'] = 'session:'  # 保存到session中的值的前缀

Session(app)

##################################################一览画面逻辑##############################################################################################
#初期todo列表显示及检索用
@app.route('/_get_todo',methods=['GET','POST'])
def get_defaluttodolist():
    #取得画面入力值
    startday_value=request.args.get('startday','',type=str)
    endday_value=request.args.get('endday','',type=str)
    sw1_value=request.args.get('sw1_setvalue','false',type=str)
    sw2_value = request.args.get('sw2_setvalue', 'false', type=str)
    title_value = request.args.get('title', '', type=str)

    #权限设定
    #公开
    if sw2_value == "false":
        auth_value = [0]
    #非公开
    elif sw2_value == "true":
        auth_value = [0,1]

    #完了是否设定
    #未完
    if sw1_value == "false":
        finish_value = [False]
    #完了
    elif sw1_value == "true":
        finish_value = [False,True]

    #标题
    if title_value =='':
        title ={"$regex":'.*',"$options":'s'}
    else:
        title = {"$regex":title_value,"$options":'s'}

    #检索日期设定
    if startday_value == ''and endday_value =='':
        # 取得当前UTC时间和3天后的UTC时间
        ISOTIMEFORMAT = "%Y-%m-%dT%H:%M:%SZ"
        utctime_today_before = (datetime.now() + timedelta(days=-1)).strftime(ISOTIMEFORMAT)
        utctime_today1 = utctime_today_before[0:10]+"T16:00:00Z"
        utctime_today = datetime.strptime(utctime_today1, ISOTIMEFORMAT)
        #utctime_3daylater1 = (utctime_today + timedelta(days=2)).strftime(ISOTIMEFORMAT)
        utctime_3daylater = utctime_today + timedelta(days=2)
    elif startday_value == '' and endday_value !='':
        # 取终了日3天前作为开始时间(UTC时间)
        ISOTIMEFORMAT = "%Y-%m-%d"
        ISOTIMEFORMAT1 = "%Y-%m-%dT%H:%M:%SZ"
        utctime_3daylater = datetime.strptime((datetime.utcfromtimestamp(datetime.strptime(endday_value,ISOTIMEFORMAT).timestamp()).strftime(ISOTIMEFORMAT))+"T16:00:00Z",ISOTIMEFORMAT1)
        utctime_today = datetime.strptime(((utctime_3daylater + timedelta(days=-2)).strftime(ISOTIMEFORMAT1)),ISOTIMEFORMAT1)
    elif startday_value != '' and endday_value =='':
        # 取开始日3天后作为终了时间(UTC时间)
        ISOTIMEFORMAT = "%Y-%m-%d"
        ISOTIMEFORMAT1 = "%Y-%m-%dT%H:%M:%SZ"
        utctime_today = datetime.strptime((datetime.utcfromtimestamp(datetime.strptime(startday_value, ISOTIMEFORMAT).timestamp()).strftime(ISOTIMEFORMAT))+"T16:00:00Z",ISOTIMEFORMAT1)
        utctime_3daylater = datetime.strptime(((utctime_today + timedelta(days=2)).strftime(ISOTIMEFORMAT1)),ISOTIMEFORMAT1)
    elif startday_value != '' and endday_value !='':
        ISOTIMEFORMAT = "%Y-%m-%d"
        ISOTIMEFORMAT1 = "%Y-%m-%dT%H:%M:%SZ"
        utctime_today = datetime.strptime((datetime.utcfromtimestamp(datetime.strptime(startday_value, ISOTIMEFORMAT).timestamp()).strftime(ISOTIMEFORMAT))+"T16:00:00Z",ISOTIMEFORMAT1)
        utctime_3daylater = datetime.strptime((datetime.utcfromtimestamp(datetime.strptime(endday_value, ISOTIMEFORMAT).timestamp()).strftime(ISOTIMEFORMAT))+"T16:00:00Z",ISOTIMEFORMAT1)

    #取出公开未完且预定今明后三天的TODO+预定完了日未填写的TODO(预定完了日+标题)
    todolist_todayand3day = mongo.db.todo.find({'权限': {"$in":auth_value}, '完了是否': {"$in":finish_value},
                                                '标题':title,
                                                '$or': [{'预定完了日': {
                                                    "$gte": utctime_today,
                                                    "$lte": utctime_3daylater}},
                                                        {'预定完了日': None}]}, {"_id": 1, "预定完了日": 1, "标题": 1})

    # 编辑显示（以时间为group条件）
    templist = []
    for row in todolist_todayand3day:
        tempdict = {}
        for key,value in row.items():
            if key == '预定完了日' :
                if value ==None :
                    tempdict['group'] = '9999-99-99'
                else :
                    tempdict['group']=value.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
            if key == '标题':
                tempdict['item']=value
            if key == '_id':
                tempdict['valueid'] = str(value)

        templist.append(tempdict)


    ISOTIMEFORMATE = "%Y-%m-%dT%H:%M:%SZ"
    utctime_today_before = (datetime.now() + timedelta(days=-1)).strftime(ISOTIMEFORMATE)
    utctime_today1 = utctime_today_before[0:10] + "T16:00:00Z"
    utctime_today_ee = datetime.strptime(utctime_today1, ISOTIMEFORMATE)

    #取出公开未完且今天必须完成的TODO(必须完了日+标题)
    musttodo_today = mongo.db.todo.find({'权限': {"$in":auth_value},'完了是否':False,'必须完了日':utctime_today_ee},{"_id":0,"必须完了日":1,"标题":1})
    # 编辑显示（今日必须完成事项以☯表示）

    for row in musttodo_today:
        for key,value in row.items():
            if key == '必须完了日':
                tempdate = value.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
            if key == '标题':
                temptitle = value
        for editedrow in templist:
            tempdict1 = dict(zip(editedrow.values(), editedrow.keys()))
            if (tempdate in tempdict1 and temptitle in tempdict1):
                editedrow.update({"item":editedrow['item']+" ☯"})
                break

    #按预定完了日的升序排序
    def sortfunction(a,b):
        if a['group'] < b['group']:
            return -1
        elif a['group'] > b['group']:
            return 1
        else:
            return 0
    templist.sort(key=functools.cmp_to_key(sortfunction))

    #去除因排序设定的9999-99-99，改成空
    for editedrow1 in templist:
        for key, value in editedrow1.items():
            if value == '9999-99-99':
                editedrow1.update({"group": ''})
                break

    return jsonify(result=templist)

@app.route('/',methods=['GET','POST'])
def init_page():
    #初始值保存在session中
    session['startday_Session'] = ''
    session['endday_Session'] = ''
    session['titleinput_name_session'] = ''
    session['sw1_Session'] = 'false'
    session['sw2_Session'] = 'false'
    return render_template('list.html')

#取得超出期限外未完成的TODO
@app.route('/_get_timeup_todo',methods=['GET','POST'])
def gettodo_timeup():
    # 取得画面入力值
    sw1_value=request.args.get('sw1_setvalue','false',type=str)
    sw2_value = request.args.get('sw2_setvalue', 'false', type=str)

    #权限设定
    #公开
    if sw2_value == "false":
        auth_value = [0]
    #非公开
    elif sw2_value == "true":
        auth_value = [0,1]

    #完了是否设定
    '''
    if sw1_value == "false":
        finish_value = False
    elif sw1_value == "true":
        finish_value = True
    '''
    # 取得当前UTC时间
    ISOTIMEFORMAT = "%Y-%m-%dT%H:%M:%SZ"
    utctime_today_before = (datetime.now() + timedelta(days=-1)).strftime(ISOTIMEFORMAT)
    utctime_today = utctime_today_before[0:10] + "T16:00:00Z"

    # 取出公开未完且必须完了日在今天之前（不含今日）的TODO(必须完了日+标题)
    undolist1 = mongo.db.todo.find({'权限': {"$in":auth_value},'完了是否':False,'必须完了日':{"$lt":datetime.strptime(utctime_today,ISOTIMEFORMAT)}},{"_id":1,"标题":1})

    undolist = []
    for row in undolist1:
        tempdict = {}
        for key, value in row.items():
            if key == '标题':
                tempdict['title'] = value
            if key == '_id':
                tempdict['value_id'] = str(value)
        undolist.append(tempdict)

    return jsonify(result=undolist)

#一览画面日期检查（from,to是合法日期,from<=to)装饰器
#详细画面日期检查（预定期限,必须期限是合法日期,预定期限<=必须期限)装饰器
def check_date():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ISOTIMEFORMAT = "%Y-%m-%d"
            from_date = request.form['startday_name']
            to_date= request.form['endday_name']
            #from,to是合法性检查
            check_error = False
            internal_check_error = False
            if (from_date != '' and to_date !=''):
                try:
                    from_date_1 = datetime.strptime(from_date,ISOTIMEFORMAT)
                    to_date_1 = datetime.strptime(to_date,ISOTIMEFORMAT)
                except:
                    check_error = True
                    #error1= "请输入正确格式的日期"
                #from<=to检查
                if check_error == False and from_date_1 > to_date_1:
                    internal_check_error = True

            elif (from_date != '' or to_date !=''):
                if from_date != '':
                    try:
                        from_date_1 = datetime.strptime(from_date, ISOTIMEFORMAT)
                    except:
                        check_error = True
                if to_date !='':
                    try:
                        to_date_1 = datetime.strptime(to_date, ISOTIMEFORMAT)
                    except:
                        check_error = True


                #返回比较结果

            return f(check_error,internal_check_error,*args, **kwargs)
        return decorated_function
    return decorator

#是否显示加密还是公开的suitch按钮值发生变动的时候
@app.route('/_switchbotton_changed',methods=['GET','POST'])
@check_date()
def sw2changed(check_error,internal_check_error):
    error1= []
    if check_error == True:
        error1.append("请输入正确格式的日期")
    if internal_check_error == True:
        error1.append("检索开始日要小于等于终了日")
    if check_error == False and internal_check_error ==False:
        # 检索值保存在session中
        session['startday_Session'] = request.form['startday_name']
        session['endday_Session'] = request.form['endday_name']
        session['titleinput_name_session'] = request.form['titleinput_name']
        if request.form['sw1_name_hidden'] == "False":
            session['sw1_Session'] = 'false'
        elif request.form['sw1_name_hidden'] == "True":
            session['sw1_Session'] = 'true'
        if request.form['sw2_name_hidden'] == "False":
            session['sw2_Session'] = 'false'
        elif request.form['sw2_name_hidden'] == "True":
            session['sw2_Session'] = 'true'
    return render_template('list.html', error=error1)

#两个swtichbotton的状态保留
@app.context_processor
def inject_statecheck():
    #sw1状态保留判断
    if "sw1_name_hidden" in request.form:
      sw1_name_hidden = request.form['sw1_name_hidden']
      if sw1_name_hidden == "False":
        statechecked = 'false'
      elif sw1_name_hidden == "True":
        statechecked = 'true'
    elif "sw1_name_hidden"  not in request.form:
        if "sw1_Session" in session:
            sw1_Session = session['sw1_Session']
            if sw1_Session == "false":
                sw1_name_hidden = "False"
                statechecked = 'false'
            elif sw1_Session == "true":
                sw1_name_hidden = "True"
                statechecked = 'true'
        else:
            statechecked = 'false'
            sw1_name_hidden='False'

    #sw2状态保留判断
    if "sw2_name_hidden" in request.form:
      sw2_name_hidden = request.form['sw2_name_hidden']
      if sw2_name_hidden == "False":
        statechecked2 = 'false'
      elif sw2_name_hidden == "True":
        statechecked2 = 'true'
    elif "sw2_name_hidden"  not in request.form:
        if "sw2_Session" in session:
            sw2_Session = session['sw2_Session']
            if sw2_Session == "false":
                sw2_name_hidden = "False"
                statechecked2 = 'false'
            elif sw2_Session == "true":
                sw2_name_hidden = "True"
                statechecked2 = 'true'
        else:
            statechecked2 = 'false'
            sw2_name_hidden='False'

    return dict(statechecked=statechecked,sw1_name_hidden_value=sw1_name_hidden, statechecked2=statechecked2,sw2_name_hidden_value=sw2_name_hidden)
###############################################################详细画面逻辑#############################################
#显示详细画面
@app.route('/_detail_display',methods=['GET','POST'])
def detail_display():

    item_id = request.args.get('item')

    ISOTIMEFORMAT = "%Y-%m-%d"
    # 标题初始化
    session['title_index'] = ''
    # 内容初始化
    session['content_index'] = ''
    # 预定期限初始化
    session['scheduleday_name'] = ''
    # 必须期限初始化
    session['mustday_name'] = ''
    #创建日初始化
    session['create_date_index'] = ''
    #权限初始化
    sw3_name_hidden_value = 'False'
    #完了初始化
    sw4_name_hidden_value = 'False'

    #新建的场合
    if item_id.strip() == '':
        buttonflag = "false"
        authchecked = "false"
        finishchecked = "false"
    #变更/删除的场合
    elif item_id.strip() != '':
        buttonflag = "true"
        # 取出item_id对应的TODO(除id以外全字段)
        undolist = mongo.db.todo.find({'_id': ObjectId(item_id)},{"_id": 0, "by":0})

        for row in undolist:
            for key, value in row.items():
                # 标题
                if key == '标题':
                    session['title_index'] = value
                # 内容
                if key == '内容':
                    session['content_index'] = value
                # 预定期限
                if key == '预定完了日':
                    if value == None:
                        session['scheduleday_name'] = ''
                    else:
                        session['scheduleday_name'] = value.astimezone(timezone(timedelta(hours=8))).strftime(ISOTIMEFORMAT)
                # 必须期限
                if key == '必须完了日':
                    if value == None:
                        session['mustday_name'] = ''
                    else:
                        session['mustday_name'] = value.astimezone(timezone(timedelta(hours=8))).strftime(ISOTIMEFORMAT)
                # 创建日
                if key == '创建日':
                    session['create_date_index'] = value.astimezone(timezone(timedelta(hours=8))).strftime(ISOTIMEFORMAT)
                # 权限
                if key == '权限':
                    if value == 0:
                        sw3_name_hidden_value =  'False'
                        authchecked = "false"
                    elif value == 1:
                        sw3_name_hidden_value = 'True'
                        authchecked = "true"
                # 完了
                if key == '完了是否':
                    if bool(value) == False:
                        sw4_name_hidden_value =  'False'
                        finishchecked = "false"
                    elif value == True:
                        sw4_name_hidden_value = 'True'
                        finishchecked = "true"

    return render_template('index.html',item_id=item_id,buttonflag=buttonflag,authchecked=authchecked,finishchecked=finishchecked,sw3_name_hidden_value=sw3_name_hidden_value,sw4_name_hidden_value=sw4_name_hidden_value)

#返回一览画面
@app.route('/_back_list',methods=['GET','POST'])
def back_list():
    from_index_return_list_value = "true"
    return render_template('list.html',from_index_return_list_value=from_index_return_list_value)

#详细画面日期检查（预定期限,必须期限是合法日期,预定期限<=必须期限)装饰器
def check_date_detail():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ISOTIMEFORMAT = "%Y-%m-%d"
            from_date = request.form['scheduleday_name']
            to_date= request.form['mustday_name']
            #from,to是合法性检查
            check_error = False
            internal_check_error = False
            if (from_date != '' and to_date !=''):
                try:
                    from_date_1 = datetime.strptime(from_date,ISOTIMEFORMAT)
                    to_date_1 = datetime.strptime(to_date,ISOTIMEFORMAT)

                except:
                    check_error = True
                    #error1= "请输入正确格式的日期"
                #from<=to检查
                if check_error == False and from_date_1 > to_date_1:
                    internal_check_error = True

            elif (from_date != '' or to_date !=''):
                if from_date != '':
                    try:
                        from_date_1 = datetime.strptime(from_date, ISOTIMEFORMAT)
                    except:
                        check_error = True
                if to_date !='':
                    try:
                        to_date_1 = datetime.strptime(to_date, ISOTIMEFORMAT)
                    except:
                        check_error = True


                #返回比较结果

            return f(check_error,internal_check_error,*args, **kwargs)
        return decorated_function
    return decorator

#详细画面提交(check->新建/更新/删除）
@app.route('/_content_update',methods=['GET','POST'])
@check_date_detail()
def content_update(check_error,internal_check_error):
    error1 = []
    # sw3状态保留判断
    if "sw3_name_hidden" in request.form:
        sw3_name_hidden = request.form['sw3_name_hidden']
        if sw3_name_hidden == "False":
            authchecked = 'false'
        elif sw3_name_hidden == "True":
            authchecked = 'true'

    # sw4状态保留判断
    if "sw4_name_hidden" in request.form:
        sw4_name_hidden = request.form['sw4_name_hidden']
        if sw4_name_hidden == "False":
            finishchecked = 'false'
        elif sw4_name_hidden == "True":
            finishchecked = 'true'

    # button状态保留
    if "buttonflag_name" in request.form:
        buttonflag = request.form['buttonflag_name']

    if check_error == True:
        error1.append("请输入正确格式的日期")
        return render_template('index.html', error=error1,buttonflag=buttonflag, authchecked=authchecked,
                               sw3_name_hidden_value=sw3_name_hidden, finishchecked=finishchecked,
                               sw4_name_hidden_value=sw4_name_hidden)
    if internal_check_error == True:
        error1.append("请确保预定期限日期在必须期限日期之前（含当天）")
        return render_template('index.html', error=error1,buttonflag=buttonflag, authchecked=authchecked,
                               sw3_name_hidden_value=sw3_name_hidden, finishchecked=finishchecked,
                               sw4_name_hidden_value=sw4_name_hidden)

    if check_error == False and internal_check_error == False:
        #追加或者更新动作

        #_id
        item_id1 = request.form['item_id_name']
        if item_id1.strip()  == '':
            item_id = ObjectId()
        else:
            item_id = ObjectId(item_id1)
        #标题
        title = request.form['title_index']
        #内容
        content = request.form['content_index']
        #权限
        sw3 = request.form['sw3_name_hidden']
        if sw3 == "False":
            auth = 0
        elif sw3 == "True":
            auth = 1
        #预定期限
        scheduleday1 = request.form['scheduleday_name']
        ISOTIMEFORMAT = "%Y-%m-%d"
        ISOTIMEFORMAT1 = "%Y-%m-%dT%H:%M:%SZ"
        if scheduleday1.strip()  == '':
            scheduleday = None
        else:
            scheduleday = datetime.strptime((datetime.utcfromtimestamp(
                datetime.strptime(scheduleday1, ISOTIMEFORMAT).timestamp()).strftime(ISOTIMEFORMAT)) + "T16:00:00Z",
                                          ISOTIMEFORMAT1)
        #必须期限
        mustday1 =  request.form['mustday_name']
        if mustday1.strip() == '':
            mustday = None
        else:
            mustday = datetime.strptime((datetime.utcfromtimestamp(
                 datetime.strptime(mustday1, ISOTIMEFORMAT).timestamp()).strftime(ISOTIMEFORMAT)) + "T16:00:00Z",
                                        ISOTIMEFORMAT1)
        #完了
        sw4 = request.form['sw4_name_hidden']
        if sw4 == "False":
            finished = False
        elif sw4 == "True":
            finished = True
        #创建日
        creatday1 = request.form['create_date_index']
        creatday = datetime.strptime((datetime.utcfromtimestamp(
            datetime.strptime(creatday1, ISOTIMEFORMAT).timestamp()).strftime(ISOTIMEFORMAT)) + "T16:00:00Z",
                                        ISOTIMEFORMAT1)

        mongo.db.todo.update_one({'_id': item_id},{'$set':{'标题':title,'内容':content,'权限':auth,'预定完了日':scheduleday,'必须完了日':mustday,'创建日':creatday,'完了是否':finished,'创建者':'ztm'}},True)
        from_index_return_list_value = "true"
        return render_template('list.html', from_index_return_list_value=from_index_return_list_value)


if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)

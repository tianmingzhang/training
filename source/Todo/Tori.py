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
from source.Todo import todo
from flask import g
import pymongo
import time




##################################################一览画面逻辑##############################################################################################
#初期todo列表显示及检索用
@todo.route('/_get_todo',methods=['GET','POST'])
def get_defaluttodolist():
    mongo1 = getattr(g, 'db', None)
    mongo = mongo1.Tori
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
    todolist_todayand3day = mongo.todo.find({'权限': {"$in":auth_value}, '完了是否': {"$in":finish_value},
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
                    tempdict['group']=value.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
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
    musttodo_today = mongo.todo.find({'权限': {"$in":auth_value},'完了是否':False,'必须完了日':utctime_today_ee},{"_id":0,"必须完了日":1,"标题":1})
    # 编辑显示（今日必须完成事项以☯表示）

    for row in musttodo_today:
        for key,value in row.items():
            if key == '必须完了日':
                tempdate = value.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
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

@todo.route('/',methods=['GET','POST'])
def init_page():
    #初始值保存在session中
    session['startday_Session'] = ''
    session['endday_Session'] = ''
    session['titleinput_name_session'] = ''
    session['sw1_Session'] = 'false'
    session['sw2_Session'] = 'false'
    return render_template('list.html')

#取得超出期限外未完成的TODO
@todo.route('/_get_timeup_todo',methods=['GET','POST'])
def gettodo_timeup():
    mongo1 = getattr(g, 'db', None)
    mongo = mongo1.Tori
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
    undolist1 = mongo.todo.find({'权限': {"$in":auth_value},'完了是否':False,'必须完了日':{"$lt":datetime.strptime(utctime_today,ISOTIMEFORMAT)}},{"_id":1,"标题":1})

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
@todo.route('/_switchbotton_changed',methods=['GET','POST'])
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
@todo.context_processor
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


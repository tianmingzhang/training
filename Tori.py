from flask import Flask
from flask import render_template
from datetime import datetime,timedelta
from flask_pymongo import PyMongo
from collections import Iterable
from flask import jsonify
import itertools
import functools
from flask import request
from functools import wraps

app = Flask(__name__)
app.config['MONGO_HOST'] = '127.0.0.1'
app.config['MONGO_PORT'] = 27017
app.config['MONGO_DBNAME'] = 'Tori'
mongo = PyMongo(app, config_prefix='MONGO')

#初期todo列表显示及检索用
@app.route('/_get_todo',methods=['GET','POST'])
def get_defaluttodolist():
    #取得画面入力值
    startday_value=request.args.get('startday','',type=str)
    endday_value=request.args.get('endday','',type=str)
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
    #未完
    if sw1_value == "false":
        finish_value = [False]
    #完了
    elif sw1_value == "true":
        finish_value = [False,True]



    #检索日期设定
    if startday_value == ''and endday_value =='':
        # 取得当前UTC时间和3天后的UTC时间
        ISOTIMEFORMAT = "%Y-%m-%dT00:00:00Z"
        utctime_today_before = datetime.utcnow()
        utctime_today1 = utctime_today_before.strftime(ISOTIMEFORMAT)
        utctime_3daylater1 = (utctime_today_before + timedelta(days=3)).strftime(ISOTIMEFORMAT)
        utctime_today = datetime.strptime(utctime_today1, ISOTIMEFORMAT)
        utctime_3daylater = datetime.strptime(utctime_3daylater1, ISOTIMEFORMAT)
    elif startday_value == '' and endday_value !='':
        # 取终了日3天前作为开始时间(UTC时间)
        ISOTIMEFORMAT = "%Y-%m-%d"
        utctime_3daylater = datetime.utcfromtimestamp(datetime.strptime(endday_value,ISOTIMEFORMAT).timestamp())
        utctime_today = (datetime.strptime(endday_value,ISOTIMEFORMAT) + timedelta(days=-3)).strftime(ISOTIMEFORMAT)
    elif startday_value != '' and endday_value =='':
        # 取开始日3天后作为终了时间(UTC时间)
        ISOTIMEFORMAT = "%Y-%m-%d"
        utctime_today = datetime.utcfromtimestamp(datetime.strptime(startday_value, ISOTIMEFORMAT).timestamp())
        utctime_3daylater = (datetime.strptime(startday_value, ISOTIMEFORMAT) + timedelta(days=3)).strftime(ISOTIMEFORMAT)
    elif startday_value != '' and endday_value !='':
        ISOTIMEFORMAT = "%Y-%m-%d"
        utctime_today = datetime.utcfromtimestamp(datetime.strptime(startday_value, ISOTIMEFORMAT).timestamp())
        utctime_3daylater = datetime.utcfromtimestamp(datetime.strptime(endday_value, ISOTIMEFORMAT).timestamp())

    #取出公开未完且预定今明后三天的TODO+预定完了日未填写的TODO(预定完了日+标题)
    todolist_todayand3day = mongo.db.todo.find({'权限': {"$in":auth_value}, '完了是否': {"$in":finish_value},
                                                '$or': [{'预定完了日': {
                                                    "$gte": utctime_today,
                                                    "$lte": utctime_3daylater}},
                                                        {'预定完了日': None}]}, {"_id": 0, "预定完了日": 1, "标题": 1})

    # 编辑显示（以时间为group条件）
    templist = []
    for row in todolist_todayand3day:
        tempdict = {}
        for key,value in row.items():
            if key == '预定完了日' :
                if value ==None :
                    tempdict['group'] = '9999-99-99'
                else :
                    tempdict['group']=value.strftime("%Y-%m-%d")
            if key == '标题':
                tempdict['item']=value

        templist.append(tempdict)


    ISOTIMEFORMAT1 = "%Y-%m-%dT00:00:00Z"
    utctime_today_before = datetime.utcnow()
    utctime_today2 = utctime_today_before.strftime(ISOTIMEFORMAT1)
    utctime_today_ee = datetime.strptime(utctime_today2, ISOTIMEFORMAT1)
    #取出公开未完且今天必须完成的TODO(必须完了日+标题)
    musttodo_today = mongo.db.todo.find({'权限': {"$in":auth_value},'完了是否':False,'必须完了日':utctime_today_ee},{"_id":0,"必须完了日":1,"标题":1})
    # 编辑显示（今日必须完成事项以☯表示）

    for row in musttodo_today:
        for key,value in row.items():
            if key == '必须完了日':
                tempdate = value.strftime("%Y-%m-%d")
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
    ISOTIMEFORMAT = "%Y-%m-%dT00:00:00Z"
    utctime_today_before = datetime.utcnow()
    utctime_today = utctime_today_before.strftime(ISOTIMEFORMAT)

    # 取出公开未完且必须完了日在今天之前（不含今日）的TODO(必须完了日+标题)
    undolist1 = mongo.db.todo.find({'权限': {"$in":auth_value},'完了是否':False,'必须完了日':{"$lt":datetime.strptime(utctime_today,ISOTIMEFORMAT)}},{"_id":0,"标题":1})

    undolist = []
    for row in undolist1:
        tempdict = {}
        for key, value in row.items():
            tempdict['title'] = value
        undolist.append(tempdict)

    return jsonify(result=undolist)

#日期检查（from,to是合法日期,from<=to)装饰器
def check_date():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ISOTIMEFORMAT = "%Y-%m-%d"
            from_date = request.form['startday_name']
            to_date= request.form['endday_name']
            #from,to是合法性检查
            try:
                from_date_1 = datetime.strptime(from_date,ISOTIMEFORMAT)
                to_date_1 = datetime.strptime(to_date,ISOTIMEFORMAT)
                check_error = False
            except:
                check_error = True
                #error1= "请输入正确格式的日期"
            #from<=to检查
            if check_error == False and from_date_1 <= to_date_1:
                internal_check_error = False
            elif check_error == False and from_date_1 > to_date_1:
                internal_check_error = True
            else:
                pass
                #error1 = "检索开始日要小于等于终了日"
            #返回比较结果

            return f(check_error,internal_check_error,*args, **kwargs)
        return decorated_function
    return decorator

#是否显示加密还是公开的suitch按钮值发生变动的时候
@app.route('/_switchbotton_changed',methods=['GET','POST'])
@check_date()
def sw2changed(check_error,internal_check_error=False):
    error1= []
    if check_error == True:
        error1.append("请输入正确格式的日期")
    if internal_check_error == True:
        error1.append("检索开始日要小于等于终了日")
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
        statechecked2 = 'false'
        sw2_name_hidden='False'

    return dict(statechecked=statechecked,sw1_name_hidden_value=sw1_name_hidden, statechecked2=statechecked2,sw2_name_hidden_value=sw2_name_hidden)



if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)

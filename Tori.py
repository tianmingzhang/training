from flask import Flask
from flask import render_template
from datetime import datetime,timedelta
from flask_pymongo import PyMongo
from collections import Iterable
from flask import jsonify

app = Flask(__name__)
app.config['MONGO_HOST'] = '127.0.0.1'
app.config['MONGO_PORT'] = 27017
app.config['MONGO_DBNAME'] = 'Tori'
mongo = PyMongo(app, config_prefix='MONGO')


@app.route('/_get_todo',methods=['GET','POST'])
def get_defaluttodolist():

    #取得当前UTC时间和3天后的UTC时间
    ISOTIMEFORMAT ="%Y-%m-%dT00:00:00Z"
    utctime_today_before = datetime.utcnow()
    utctime_today = utctime_today_before.strftime(ISOTIMEFORMAT)
    type(utctime_today)
    utctime_3daylater = (utctime_today_before + timedelta(days=3)).strftime(ISOTIMEFORMAT)

    #取出公开未完且预定今明后三天的TODO+预定完了日未填写的TODO(预定完了日+标题)
    todolist_todayand3day = mongo.db.todo.find({'权限': 0, '完了是否': False,
                                                '$or': [{'预定完了日': {
                                                    "$gte": datetime.strptime(utctime_today, ISOTIMEFORMAT),
                                                    "$lte": datetime.strptime(utctime_3daylater, ISOTIMEFORMAT)}},
                                                        {'预定完了日': None}]}, {"_id": 0, "预定完了日": 1, "标题": 1})

    # 编辑显示（以时间为group条件）
    templist = []
    for row in todolist_todayand3day:
        tempdict = {}
        for key,value in row.items():
            if key == '预定完了日' :
                if value ==None :
                    tempdict['group'] = ''
                else :
                    tempdict['group']=value.strftime("%Y-%m-%d")
            if key == '标题':
                tempdict['item']=value

        templist.append(tempdict)



    #取出公开未完且今天必须完成的TODO(必须完了日+标题)
    musttodo_today = mongo.db.todo.find({'权限': 0,'完了是否':False,'必须完了日':datetime.strptime(utctime_today,ISOTIMEFORMAT)},{"_id":0,"必须完了日":1,"标题":1})
    # 编辑显示（今日必须完成事项以☯表示）

    for row in musttodo_today:
        for key,value in row.items():
            if key == '必须完了日':
                tempdate = value.strftime("%Y-%m-%d")
            if key == '标题':
                temptitle = value
        for editedrow in templist:
            tempflag = 0
            for key,value in editedrow.items():
                if key == 'group' and value == tempdate:
                    tempflag = 1
                if key == 'item' and tempflag == 1 and value == temptitle:
                    editedrow.update({key:value+" ☯"})

    return jsonify(result=templist)

@app.route('/',methods=['GET','POST'])
def init_page():
    return render_template('list.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)

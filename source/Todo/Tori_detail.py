from flask import Flask,session
from flask import render_template
from datetime import datetime,timedelta,timezone
from flask import jsonify
from flask import request,make_response,send_from_directory
from functools import wraps
from flask_session import Session
from bson.objectid import ObjectId
from source.Todo import todo
from flask import g
import gridfs
import configparser
import os

###############################################################详细画面逻辑#############################################
#显示详细画面
@todo.route('/_detail_display',methods=['GET','POST'])
def detail_display():
    mongo1 = getattr(g, 'db', None)
    mongo = mongo1.Tori
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
        undolist = mongo.todo.find({'_id': ObjectId(item_id)},{"_id": 0, "by":0})

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
                        session['scheduleday_name'] = value.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime(ISOTIMEFORMAT)
                # 必须期限
                if key == '必须完了日':
                    if value == None:
                        session['mustday_name'] = ''
                    else:
                        session['mustday_name'] = value.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime(ISOTIMEFORMAT)
                # 创建日
                if key == '创建日':
                    session['create_date_index'] = value.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime(ISOTIMEFORMAT)
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

                #附件
                entries = []
                tempdict = {}
                if key.startswith('附件'):
                    tempdict['fileid']  = value['fileid']
                    tempdict['filename'] = value['filename']
                    entries.append(tempdict)

    return render_template('index.html', item_id=item_id, buttonflag=buttonflag, authchecked=authchecked, finishchecked=finishchecked, sw3_name_hidden_value=sw3_name_hidden_value, sw4_name_hidden_value=sw4_name_hidden_value,entries=entries)

#返回一览画面
@todo.route('/_back_list',methods=['GET','POST'])
def back_list():
    from_index_return_list_value = "true"
    return render_template('list.html', from_index_return_list_value=from_index_return_list_value)

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
@todo.route('/_content_update',methods=['GET','POST'])
@check_date_detail()
def content_update(check_error,internal_check_error):
    mongo1 = getattr(g, 'db', None)
    mongo = mongo1.Tori
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
        return render_template('index.html', error=error1, buttonflag=buttonflag, authchecked=authchecked,
                               sw3_name_hidden_value=sw3_name_hidden, finishchecked=finishchecked,
                               sw4_name_hidden_value=sw4_name_hidden)
    if internal_check_error == True:
        error1.append("请确保预定期限日期在必须期限日期之前（含当天）")
        return render_template('index.html', error=error1, buttonflag=buttonflag, authchecked=authchecked,
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

        mongo.todo.update_one({'_id': item_id},{'$set':{'标题':title,'内容':content,'权限':auth,'预定完了日':scheduleday,'必须完了日':mustday,'创建日':creatday,'完了是否':finished,'创建者':'ztm'}},True)
        from_index_return_list_value = "true"
        return render_template('list.html', from_index_return_list_value=from_index_return_list_value)

#文件上传
@todo.route('/_add_file',methods=['GET','POST'])
def add_file():
    # 取得画面选中的文件
    file = request.files['fileup']
    #取得该条记录对应的TODO_ID
    item_id1 = request.form['item_id']
    #取得文件的序列号
    no = request.form['num']
    #处理结果
    resulta = {}

    if item_id1.strip() == '':
        #新规场合：_id先暂存，依旧可以删除（从_id list)，查看，但是正式登陆要随新规按钮一起动作
        pass
    else:
        # 更新：_id直接存入对应的document，删除也直接从document，文件和更新按钮动作分开
        item_id = ObjectId(item_id1)
        title = '附件'+ no

        mongo1 = getattr(g, 'db', None)
        mongo = mongo1.Tori
        fs = gridfs.GridFS(mongo)
        #print('file\'s type is %s'% (type(file)))

        with fs.new_file(filename=file.filename) as fp:
          fp.write(file)

        title_value ={'fileid':fp._id,'filename':file.filename}
        mongo.todo.update_one({'_id': item_id}, { '$push': {title:title_value}}, False)


        #返回处理结果
        resulta['result'] = 0
        resulta['mode'] = 1 #更新模式
        resulta['filename'] = file.filename
        resulta['fileid'] = str(fp._id)
        resulta['fieldname'] = title
    return jsonify(result=resulta)

#文件下载查看
@todo.route('/_download_file/<string:fileid>',methods=['GET','POST'])
def download_file(fileid):
    mongo1 = getattr(g, 'db', None)
    mongo = mongo1.Tori
    fs = gridfs.GridFS(mongo)
    # 取得画面入力值
    #fileid = request.args.get('fileid', '', type=str)
    # get db parameter
    config = configparser.ConfigParser()
    config.read('parameter.ini')
    dir = config.get('FILE', 'tempdir')

    # 下载文件
    with fs.get(ObjectId(fileid)) as fp_read:
        with open(dir+fp_read.filename, 'wb') as f:
            f.write(fp_read.read())
    #with fs.get(ObjectId(fileid)) as fp_read:
            #out= fp_read
    # 处理结果
    #resulta = dir+fp_read.filename
    #with open(resulta,'rb') as r:
        #data = r.read()
        #print("file data:%s"% data)
    #resp = make_response(data)
    #resp.headers['Content-Type'] = 'application/octet-stream'
    #resp.headers['Content-Disposition'] = 'attachment; '
    return send_from_directory(dir,fp_read.filename,as_attachment =True)

# 文件删除
@todo.route('/_del_file/<string:fileid>', methods=['GET', 'POST'])
def del_file(fileid):
    mongo1 = getattr(g, 'db', None)
    mongo = mongo1.Tori
    fs = gridfs.GridFS(mongo)
    #return value
    resulta = {}
    # get db parameter
    config = configparser.ConfigParser()
    config.read('parameter.ini')
    dir = config.get('FILE', 'tempdir')

    #getparameter
    item_id1 = request.args.get('item_id', '', type=str)
    item_id = ObjectId(item_id1)
    fieldname = request.args.get('fieldname', '', type=str)

    with fs.get(ObjectId(fileid)) as fp_read:
        filename = fp_read.filename

    #中间文件删除
    try:
      os.remove(dir+filename)
    except OSError as e:
        resulta['result'] = 1
        return resulta
    except Exception as e:
        print(e)

    #GridFS里的文件删除
    try:
      if fs.exists(fileid) :
         fs.delete(fileid)
    except Exception as e:
        resulta['result'] = 1
        return resulta

    # record记录里的file-id删除
    try:
        mongo.todo.update_one({'_id': item_id}, {'$unset': {fieldname: 1}})
    except Exception as e:
        resulta['result'] = 1
        return resulta

    # 返回处理结果
    resulta['result'] = 0
    resulta['mode'] = 1  # 更新模式
    return resulta
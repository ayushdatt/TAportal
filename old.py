# coding: utf8

#########################################################################
## This is a samples controller
## - index is the default action of any application
## - user is required for authentication and authorization
## - download is for downloading files uploaded in the db (does streaming)
## - call exposes all registered services (none by default)
#########################################################################  


from gluon.sqlhtml import form_factory
import socket
from reportlab.platypus import *
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from uuid import uuid4
from cgi import escape
import os
import ldap
import re
OrderedDict=local_import('ordereddict')


CAS.login_url='https://login.iiit.ac.in/cas/login'
CAS.check_url='https://login.iiit.ac.in/cas/validate'
CAS.logout_url='https://login.iiit.ac.in/cas/logout'
#CAS.my_url='http://taship.iiit.ac.in/taship/default/login'
CAS.my_url='http://localhost:8000/taship/default/login'


# User's Roles
user_roles = {"none": 0,
              "admin": 1,
              "student": 2,
              "faculty": 3}

#---------- Global VAriables ----------------------------------------
name=""
roll=""
fac=[]

# print "sesion", session

# ---------- HOME PAGE IS SAME FOR ALL THE USERS --------------------

if not session.username and not request.function=='login':
    redirect(URL(r=request, f='login'))

#-------------------------------------------------------------------------------
def login():
    session.role = user_roles["none"]
    session.username = CAS.login(request)
    sem=db(db.Semester.id>0).select()
    if sem:
       session.current_semester = sem[0].semname
    return dict(message="taship")
#-------------------------------------------------------------------------------

def retrieveUserInfo():
    global name
    global roll
    l = ldap.initialize("ldap://ldap.iiit.ac.in")
    username = session.username
    password = session.password
    l.protocol_version = ldap.VERSION3  
   
    baseDN = "ou=Users,dc=iiit,dc=ac,dc=in"
    searchScope = ldap.SCOPE_SUBTREE
    searchFilter = "mail="+username
    
    result = l.search_s(baseDN, searchScope, searchFilter)
    entry = result[0]
    name = entry[1]['cn'][0]
    if 'uidNumber' in entry[1]:
        roll = entry[1]['uidNumber'][0]
    else:
        roll = entry[1]['uid'][0]
#-------------------------------------------------------------------------------
def logout():
    u=None
    if session.role == user_roles["admin"]:
        u="admin"
    elif session.role == user_roles["student"]:
        u="student"
    elif session.role== user_roles["faculty"]:
        u="faculty"
    db.auth_event.insert(description="logged out",origin=session.username,user_type=u,name=session.name,uid=session.roll)
    
    session.username=None
    CAS.logout()
#-------------------------------------------------------------------------------
def cprofile_display():
    if session.role != user_roles["admin"] and session.role != user_roles["faculty"]:
        redirect(URL(r=request,f='index'))
        return dict()
    id1=request.args(0)
            
    rows1 = db(db.Course.cid==id1).select()
    response.flash=id1
    return dict(rows1=rows1)

#-------------------------------------------------------------------------------
def home_page():
    # Retrieve User information from ldap
    retrieveUserInfo()
    # Save name and roll number of user
    session.name = name
    session.roll = roll

    if session.role == user_roles["none"]:
        session.mark = {}
        emailValue = db(db.Admin.ademail_id == session.username).select(db.Admin.ademail_id)
        if emailValue:
            # Admin
            db.auth_event.insert(origin=session.username,user_type="admin",description="logged in",name=session.name,uid=session.roll)
            redirect(URL(r=request,f='sp_check'))
        
        if session.username:
            email_domain = session.username.split('@')[1]
            if email_domain == "students.iiit.ac.in" or email_domain == "research.iiit.ac.in":
                # Student
                db.auth_event.insert(origin=session.username,user_type="student",description="logged in",name=session.name,uid=session.roll)
                session.role = user_roles["student"]
                session.student_email = session.username
                query = db(db.Applicant.aprollno == session.roll).select().first()
                if query:
                    if not db(db.SelectedTA.appid == query.id).select():
                        query.apemail_id = session.student_email
                        query.update_record()
                        #query = db(db.Applicant.aprollno == session.roll).update(apemail_id = session.student_email)
                    else:
                        session.student_email = query.apemail_id
            elif email_domain == 'iiit.ac.in':
                # Faculty
                db.auth_event.insert(origin=session.username,user_type="faculty",description="logged in",name=session.name,uid=session.roll)
                session.faculty_login_emailid = session.username
                session.role = user_roles["faculty"]
                session.username = session.username

    return dict(message=session.username)
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def sp_check():
    return dict(message="taship")
#-------------------------------------------------------------------------------

#----------------- General Function for all ------------------------------------
def courses_info():
    r=db((db.Course.id==db.Teach.course_id) & (db.Teach.faculty_id == db.Faculty.id))\
        .select(db.Course.cname,db.Course.cid,db.Course.cdts,db.Course.hours_per_week,db.Faculty.fname,orderby=db.Course.cname.upper())
    return  dict(r=r)

#-------------------------------------------------------------------------------

#----------------- General Function for all ------------------------------------
def contacts():
    r=db(db.Admin.id>0).select()
    return dict(r=r)
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def match_password(email, passwd,addr): 
# FUNCTION FOR VALIDATION OF USERNAME AND PASSWORD 
    f = email.split('@')
    username = f[0]
    try:
        address = addr 
        service_port = 61237
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((address,service_port))
        tosend = 'auth ' + username + ' ' + passwd + '\r\n' # authorization format
        sent = s.send(tosend)
        chunk = s.recv(128)
        s.close()
        if (chunk == '1 match'+'\n' ):
            return '1';
    except:
        return False
#-------------------------------------------------------------------------------

## --------------------- TEMPORARY ---------------------------------------------
#def truncate():
# FUNCTION TO DELETE ALL THE ENTRIES OF THE TABLE 
#   db.Course.truncate()
#   db.Applicant.truncate()
#   db.Faculty.truncate()
#   db.Semester.truncate()
#   db.AppliedFor.truncate()
#   db.OfferedTo.truncate()
#   db.Teach.truncate()
#   db.SelectedTA.truncate()

#   return dict()
#-------------------------------------------------------------------------------

# -----  NEWMAIL FUNCTION FOR SENDING MAILS TO THE ADMIN FACULTY AND TAS -------
import smtplib
import gluon

class NewMail(object):
    def __init__(self):
        self.settings = gluon.tools.Settings()
        self.settings.server = 'smtp.gmail.com:587'
        self.settings.use_tls = True
        self.settings.sender = ''
        self.settings.login = ""
        self.settings.lock_keys = True
    def send(self,to,subject,message):
        try:
            (host, port) = self.settings.server.split(':')
            server = smtplib.SMTP(host, port)
            if self.settings.login:
                server.ehlo()
                server.ehlo()
                (username, password) = self.settings.login.split(':')
            message = "From: %s\n"%(self.settings.sender)+"To: %s\n" %(to)+"Subject: %s\n" % (subject)+"\r\n"+(message)+"\r\n"
            server.sendmail(self.settings.sender, to, message)
            server.quit()
        except Exception, e:
            print e
            return False
        return True
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def sendmail(sender,reciever,subj,title):

    mail=NewMail()
    # specify server
    mail.settings.server='mail.iiit.ac.in:25'
    mail.settings.login='username:password' or None

# specify address to send as
    mail.settings.sender=sender

#   mail.settings.lock_keys=True
    mail.settings.use_tls=True
#       return mail.settings.keys()
#send the message
    print "Mail to be sent"
    return mail.send(to=reciever, subject=title, message=subj)
# ----->>>  mail server is kept "mail.iiit.ac.in" <<<<--------------------------
#-------------------------------------------------------------------------------

# -------------- Applicant related queries  starts here ------------------------

# --------------- Refactored ---------------------------------------------------
def getUpdateProfileForm():
    """
        Returns the Student Update Profile form
    """
    form = form_factory(
            SQLField('name', 'string', label = 'Name', requires = IS_NOT_EMPTY()),
            SQLField('rollno', 'integer', label = 'Roll No',requires = IS_NOT_EMPTY()),
            SQLField('program', label = 'Program Of Study', requires = IS_IN_DB(db,'Program.id','%(pname)s')),
            SQLField('cgpa', 'double', label='CGPA',requires = IS_FLOAT_IN_RANGE(0,10)),
            SQLField('phone', 'string', label = 'Phone No'),
            SQLField('prevexp',label = 'Previous Experience',requires=IS_IN_SET(['Yes','No'])),
            )

    return form

# --------------- Refactored ---------------------------------------------------
def getAddPreferenceForm():
    """
        Returns the form for adding a preference
    """
    appid = db(db.Applicant.apemail_id == session.student_email).select(db.Applicant.id)[0]
    # Number of courses for which applicant has applied
    num_applied_courses = db(db.AppliedFor.appid == appid).count()
    pref_rem = [num_applied_courses + 1]
    form = form_factory(                        # creating a form for the applicant to select course
            SQLField('course', label = 'Course', requires = (IS_IN_DB(db, 'Course.id', '%(cname)s ( %(cid)s )'))),
            SQLField('grade', label = 'Grade In The Course', requires = IS_IN_SET(['A','A-','B','B-','C','NA'])),
            SQLField('preference', label = 'Preference', requires = IS_IN_SET(pref_rem)),_method='GET')
    return form

# --------------- Refactored ---------------------------------------------------
def getUpdatePhoneForm():
    """
    """
    form = form_factory(
        SQLField('phone', 'string', label = 'Phone No'),
        SQLField('prevexp',label = 'Previous Experience',requires=IS_IN_SET(['Yes','No'])),
        SQLField('program', label = 'Program Of Study', requires = IS_IN_DB(db,'Program.id','%(pname)s')))
    return form

# --------------- Refactored ---------------------------------------------------
def checkPortalActivity():
    """
        Checks if the portal is active for the student.
        Displays an appropriate message if inactive
        Returns true if active
    """
    now = datetime.datetime.now()
    portal_date=db(db.Portaldate.id>0).select()
    if portal_date:
        start=portal_date[0].start_date
        end=portal_date[0].end_date
        if now < start:
            # Application not yet open
            session.flash = 'Wait till %s'%start.strftime('%d %B %Y %I:%M%p')
            redirect(URL(r=request,f='home_page'))
        elif now > end:
            # Application deadline over
            session.flash = 'Deadline over at %s'%end.strftime('%d %B %Y %I:%M%p')
            redirect(URL(r=request,f='home_page'))
    else :
        session.flash = 'Portal not yet Started  !!'
        redirect(URL(r=request,f='home_page'))
    return True

# --------------- Refactored ---------------------------------------------------
def getStudentInfo():
    """
        Queries and returns the students info from db
    """
    return db((db.Applicant.apemail_id == session.student_email) &
            (db.Applicant.program_id == db.Program.id)).select()

# --------------- Refactored ---------------------------------------------------
def checkIsStudent():
    """
        Redirects to index if the current user is not student
    """
    if session.role != user_roles["student"]:
        redirect(URL(r = request , f = 'index'))

#---------------modified by Team 45---------------------------------------------
def Fill_missing_student_info():
    '''
        Generates form for filling the remaining student info for records taken from dump file.
    '''
    form = form_factory(
        SQLField(
            'phone', 'string', label='Phone No'), SQLField(
            'prevexp', label='Previous Experience', requires=IS_IN_SET(
                [
                    'Yes', 'No'])), SQLField(
                        'program', label='Program Of Study', requires=IS_IN_DB(
                            db, 'Program.id', '%(pname)s')))
    if form.accepts(request.vars, session):
        db(
            db.Applicant.apemail_id == session.student_email).update(
            phoneno=request.vars.phone,
            program_id=request.vars.program,
            prev_exp=request.vars.prevexp)
        redirect(URL(r=request, f='TA_application'))
    return dict(form=form)


def generate_course_preference_form(appid):
    '''
        Generates course preference form by fetching last max preference
    '''
    course = db(db.AppliedFor.appid == appid).select(
    )  # ---- courses for which applicant has applied
    pref_sel = []  # ---- preferences corresponding applied courses
    for rows in course:
        if rows.preference:
            pref_sel.append(int(rows.preference))
    pref_rem = []
    check1 = 0
    lenght = len(pref_sel)
    if lenght >= 1:
        check1 = max(pref_sel)
    pref_rem = [check1 + 1]
    form = form_factory(                        # creating a form for the applicant to select course
        SQLField(
            'course',
            label='Course',
            requires=(
                IS_IN_DB(
                    db,
                    'Course.id',
                    '%(cname)s ( %(cid)s )'))),
        SQLField('grade', label='Grade In The Course',
                 requires=IS_IN_SET(['A', 'A-', 'B', 'B-', 'C', 'NA'])),
        SQLField('preference', label='Preference', requires=IS_IN_SET(pref_rem)), _method='GET')
    return form


def confirm_and_log_course_app(appid, course, grade, preference):
    ''' Functionalities:
        1.Inserts the applied course preference in database
        2.Makes a log for the record
    '''
    db.AppliedFor.insert(
        appid=appid,
        cid=course,
        noflag=0,
        timestamp=datetime.date.today(),
        grade=grade,
        preference=preference)
    c = db(db.Course.id == course).select()[0]
    db.auth_event.insert(
        origin=session.student_email,
        user_type="student",
        description="applied for" +
        c.cname,
        name=session.name,
        uid=session.roll)
    Course = db(db.Course.id == course).select(db.Course.cname)
    for i in Course:
        course = i.cname
    x = ""
    t = datetime.datetime.now()
    if t.month < 7:
        x = str(t.year) + " " + "Spring"
    else:
        x = str(t.year) + " " + "Monsoon"
    query = db(
        (db.logs.cname == course) & (
            db.logs.time == x)).select(
        db.logs.id)
    flag_c = 0
    entry = 0
    for i in query:
        entry = i.id
    qu = db(db.Applicant.id == appid).select(db.Applicant.aprollno)
    roll = 0
    for i in qu:
        roll = i.aprollno
    if entry > 0:
        flag_c = 1
    t = datetime.datetime.now()
    if flag_c == 1:
        q = db(db.logs.cname == course).select(db.logs.No_of_TAs_applied)
        p = q[0].No_of_TAs_applied
        p += 1
        db(db.logs.id == entry).update(No_of_TAs_applied=p)
        db.logs_applicant.insert(
            logid=entry,
            applicant_id=roll,
            applicant_name=session.name,
            applicantid=session.student_email,
            Status='None')
    else:
        q = db(db.Course.cname == course).select(db.Course.cid)
        for i in q:
            cd = i.cid
            db.logs.insert(time=x, cname=course, cid=cd, No_of_TAs_applied=1)
            query = db(db.logs.cname == course).select(db.logs.id)
        for i in query:
            entry = i.id
        db.logs_applicant.insert(
            logid=entry,
            applicant_id=roll,
            applicant_name=session.name,
            applicantid=session.student_email)
    session.flash = '!! Thank You for Application !!'
    redirect(URL(r=request, f='TA_application'))


def Register_student_applicant():
    '''
        Registers a new applicant
    '''
    if db(db.Applicant.apemail_id == session.student_email).select():
        redirect(URL(r=request, f='TA_application'))
    form = form_factory(
        SQLField(
            'name', 'string', label='Name', requires=IS_NOT_EMPTY()), SQLField(
            'rollno', 'integer', label='Roll No', requires=IS_NOT_EMPTY()), SQLField(
                'program', label='Program Of Study', requires=IS_IN_DB(
                    db, 'Program.id', '%(pname)s')), SQLField(
                        'cgpa', 'double', label='CGPA', requires=IS_FLOAT_IN_RANGE(
                            0, 10)), SQLField(
                                'phone', 'string', label='Phone No'), SQLField(
                                    'prevexp', label='Previous Experience', requires=IS_IN_SET(
                                        [
                                            'Yes', 'No'])), )
    session.check = 0
    # ----------------- if the form is submitted ----------------------------
    if form.accepts(request.vars, session):
        name = request.vars.name
        rollno = request.vars.rollno
        program = request.vars.program
        cgpa = request.vars.CGPA
        phone = request.vars.phone
        exp = request.vars.prevexp
        # ----------- insert the applicant ----------
        appid = db.Applicant.insert(
            apname=name,
            aprollno=rollno,
            apemail_id=session.student_email,
            apcgpa=cgpa,
            phoneno=phone,
            prev_exp=exp,
            program_id=program)
        db.auth_event.insert(
            origin=session.student_email,
            user_type="student",
            description="profile updated",
            name=session.name,
            uid=session.roll)
        mesg = "!! Profile Created !! "
        redirect(URL(r=request, f='TA_application'))
    return dict(form=form)


#---------------modified by Team 45---------------------------------------
def TA_application():
   # checking whether applicant is logged in or not
    print "before"
    print str(session.login)
    if session.role != user_roles["student"]:
        redirect(URL(r=request, f='index'))
        return dict()
    print "inside"
    session.check = 0
    check_point = 0
    msg = '' 
    record = []
    session.already_applied = 0
    now = datetime.datetime.now()
    portal_date = db(db.Portaldate.id > 0).select()
    now = datetime.datetime.now()
    records_appliedfor = db(
        (db.AppliedFor.appid == db.Applicant.id) & (
            db.AppliedFor.cid == db.Course.id) & (
            db.Applicant.apemail_id == session.student_email)).select(
                orderby=db.AppliedFor.preference)

    if portal_date:  # ------check if there is a record in portal_date
        start = portal_date[0].start_date
        end = portal_date[0].end_date
        if now < start:
            session.flash = 'Wait till %s' % start.strftime('%d %B %Y %I:%M%p')
            redirect(URL(r=request, f='home_page'))
        elif now > end:
            session.flash = 'Deadline over at %s' % end.strftime(
                '%d %B %Y %I:%M%p')
            redirect(URL(r=request, f='home_page'))
        elif now > start and now < end:
            # if an applicant is already applied
            if db(db.Applicant.apemail_id == session.student_email).select():
                session.already_applied = 1
                applicantInfo = db(
                    (db.Applicant.apemail_id == session.student_email) & (
                        db.Applicant.program_id == db.Program.id)).select()
                appid = db(
                    db.Applicant.apemail_id == session.student_email).select(
                    db.Applicant.id)[0]
                if (db(db.Applicant.apemail_id == session.student_email).select(
                        db.Applicant.phoneno)[0].phoneno) == None:
                    redirect(URL(r=request, f='Fill_missing_student_info'))
                else:
                    session.check = 1
                    form = generate_course_preference_form(appid)

            else:
                                            # ------------ else if the applican
                redirect(URL(r=request, f='Register_student_applicant'))

            # ----------------- if the form is submitted ----------------------
            if form.accepts(request.vars, session):
                name = request.vars.name
                rollno = request.vars.rollno
                program = request.vars.program
                course = request.vars.course
                grade = request.vars.grade
                cgpa = request.vars.CGPA
                phone = request.vars.phone
                exp = request.vars.prevexp
                preference = request.vars.preference
                if(session.already_applied == 1):
                    r = db(
                        db.Applicant.apemail_id == session.student_email).select()
                    for rows in applicantInfo:
                        appid = rows.Applicant.id

                if(session.already_applied == 1):
                    s = db(
                        (db.AppliedFor.appid == appid) & (
                            db.AppliedFor.cid == course)).select().first()
                    if(s):
                        a = 1
                        session.flash = '!! You applied for course !!'
                        redirect(URL(r=request, f='TA_application'))
                    else:                # else fill info in the database
                        confirm_and_log_course_app(
                            appid,
                            course,
                            grade,
                            preference)

                else:
                    session.flash = mesg
                    redirect(URL(r=request, f='TA_application'))
    else:
        session.flash = 'Portal not yet Started  !!'
        redirect(URL(r=request, f='home_page'))
    return dict(records_appliedfor=records_appliedfor, form=form)
#-------------------------------------------------------------------------

def edit_profile():
    """
        Displays a form to let a student edit his profile.
    """
    if (session.role != 2):
        redirect(URL(r=request, f='index'))
        return dict()
    student_details = db(
        (db.Applicant.apemail_id == session.student_email) & (
            db.Applicant.program_id == db.Program.id)).select()
    if len(student_details) == 0:  # if student details are not available
        redirect(URL(r=request, f='index'))
    student_details = student_details.first()

    form = form_factory(
        SQLField(
            'NAME',
            'string',
            label='Name',
            requires=IS_NOT_EMPTY(),
            default=student_details['Applicant'].apname),
        SQLField(
            'rollno',
            'integer',
            label='Roll No',
            requires=IS_NOT_EMPTY(),
            default=student_details['Applicant'].aprollno),
        SQLField(
            'program',
            label='Program Of Study',
            requires=IS_IN_DB(
                db,
                'Program.id',
                '%(pname)s'),
            default=student_details['Applicant'].program_id),
        SQLField(
            'cgpa',
            'double',
            default=student_details['Applicant'].apcgpa,
            label='CGPA',
            requires=IS_FLOAT_IN_RANGE(
                0,
                10)),
        SQLField(
            'phone',
            'string',
            label='Phone No',
            default=student_details['Applicant'].phoneno),
        SQLField(
            'prevexp',
            label='Previous Experience',
            requires=IS_IN_SET(
                [
                    'Yes',
                    'No']),
            default=student_details['Applicant'].prev_exp))

    if form.accepts(request.vars, session):
        student_details['Applicant'].apname = request.vars.name
        student_details['Applicant'].aprollno = request.vars.rollno
        student_details['Applicant'].program_id = request.vars.program
        student_details['Applicant'].phoneno = request.vars.phone
        student_details['Applicant'].prev_exp = request.vars.prevexp
        student_details['Applicant'].cgpa = request.vars.cgpa
        student_details['Applicant'].update_record()
        response.flash = '!! profile updated !!'
        redirect(URL(r=request, f='student_profile'))
    return dict(form=form)
#-------------------------------------------------------------------------------

def unselect_course():
    # checking whether user is student or not
    checkIsStudent()

    appid=db(db.Applicant.apemail_id == session.student_email).select(db.Applicant.id)[0]     #----stores the applicant id of current user
    appcor=db((db.AppliedFor.appid == appid)&(db.AppliedFor.cid==db.Course.id)).select()     #-----stores all courses for which user has applied
    form = form_factory(                        # -------- creating form for unselecting  course --------------         
    SQLField('course', label = 'Select Course '))
    return dict(form=form,appid=appid,appcor=appcor)
#-------------------------------------------------------------------------------

def get_portal_state():
    """ Returns the state of the portal:

            0-stands for not active yet
            1-stands for active and accepting
            2-stands for active but not accepting i.e. date exceeded
    """

    portal_date = db(db.Portaldate.id > 0).select()
    now = datetime.datetime.now()
    start = portal_date[0].start_date
    end = portal_date[0].end_date
    if now < start:
        return 0
    elif now > start and now < end:
        return 1
    else:
        return 3


def status():
    """
        Controller for the status of applications.
        Functionalities :
            1. Increase Preference for a Course
            2. Decrease Preference for a Course
            3. Accept an offer
            4. Reject an offer
    """
    var_new = 0
    appid = db(
        db.Applicant.apemail_id == session.student_email).select(
        db.Applicant.id)[0]  # ----stores the applicant id of current user

    courses_applied_for = db(
        (db.AppliedFor.appid == db.Applicant.id) & (
            db.AppliedFor.cid == db.Course.id) & (
            db.Applicant.apemail_id == session.student_email)).select(
                orderby=db.AppliedFor.preference)
    status_of_applied_courses = db(
        (db.AppliedFor.appid == db.Applicant.id) & (
            db.AppliedFor.cid == db.Course.id) & (
            db.Applicant.apemail_id == session.student_email)).select(
                db.AppliedFor.status)
    selected = 0

    # if student has already accepted to be TA of a course
    for course in status_of_applied_courses:
        if course.status == 'Selected':
            selected = 1

    portal_date = db(db.Portaldate.id > 0).select()
    if portal_date:
        state = get_portal_state()
        if state == 0:
            # if time for applications hasn't begun
            session.flash = 'Wait till %s' % start.strftime('%d %B %Y %I:%M%p')
            redirect(URL(r=request, f='index'))

        elif state == 1:
            # if time of application is still running
            if request.vars.index:
                index = int(request.vars.index)
            apfid = request.vars.apfid

            if request.vars.submit == 'up':
                status_up(index, courses_applied_for)
            elif request.vars.submit == 'down':
                if index < len(courses_applied_for) - 1 and index >= 0:
                    status_down(index, courses_applied_for)

        else:  # if time for applications is over
            state = 0

        if selected == 1:
            state = 2
            if request.vars.submit == 'accept':
                var_new = 0
                accept_offer(appid)

            elif request.vars.submit == 'reject':
                reject_offer(appid)
    else:
        state = 0
    return dict(
        records_appliedfor=courses_applied_for,
        state=state,
        records=courses_applied_for,
        flag=selected,
        new=var_new)


def status_up(index, courses_applied_for):
    """
        Changes the preference of the course at 'index' to a level higher
    """
    pref_curr = int(courses_applied_for[index].AppliedFor.preference)

    if index < len(courses_applied_for) and index > 0:
        pref_prev = int(courses_applied_for[index - 1].AppliedFor.preference)
        if pref_curr == pref_prev + 1:
            db(db.AppliedFor.id == courses_applied_for[index].AppliedFor.id).update(
                preference=pref_prev)
            db(db.AppliedFor.id == courses_applied_for[
               index - 1].AppliedFor.id).update(preference=pref_curr)
        elif pref_curr > pref_prev + 1:
            db(db.AppliedFor.id == courses_applied_for[index].AppliedFor.id).update(
                preference=pref_curr - 1)

    elif index == 0:
        if pref_curr != 1:
            db(db.AppliedFor.id == courses_applied_for[index].AppliedFor.id).update(
                preference=pref_curr - 1)

    redirect(URL(r=request, f='status'))


def status_down(index, courses_applied_for):
    """
        Changes the preference of the course at 'index' to a level lower
    """
    pref_curr = int(courses_applied_for[index].AppliedFor.preference)
    pref_next = int(courses_applied_for[index + 1].AppliedFor.preference)
    if pref_curr == pref_next - 1:
        db(db.AppliedFor.id == courses_applied_for[index].AppliedFor.id).update(
            preference=pref_next)
        db(db.AppliedFor.id == courses_applied_for[
           index + 1].AppliedFor.id).update(preference=pref_curr)
    elif pref_curr < pref_next - 1:
        db(db.AppliedFor.id == courses_applied_for[index].AppliedFor.id).update(
            preference=pref_curr + 1)
    redirect(URL(r=request, f='status'))


def reject_offer(appid):
    """
        Rejects the offered position to 'appid'
    """

    course = db(db.Course.id == request.vars.cid).select()[0]
    c = db(db.logs.cname == course.cname).select(db.logs.id)[0]
    db((db.logs_applicant.applicantid == session.student_email) &
       (db.logs_applicant.logid == c.id)).update(Status='Rejected')
    Id1 = db(
        (db.AppliedFor.appid == appid) & (
            db.AppliedFor.cid == request.vars.cid)).select()
    Id2 = db(db.SelectedTA.appid == appid).select()[0]
    if Id1 and Id2:
        db((db.AppliedFor.appid == appid) &
           (db.AppliedFor.cid == request.vars.cid)).delete()
        TA_query = db(db.SelectedTA.appid == appid).select()[0]
        if TA_query.TAtype == 'quarter':
            No_of_Type = db(
                db.Course.id == request.vars.cid).select()[0].no_of_qta
            db(db.Course.id == request.vars.cid).update(
                no_of_qta=No_of_Type - 1)
        elif TA_query.TAtype == 'half':
            No_of_Type = db(
                db.Course.id == request.vars.cid).select()[0].no_of_hta
            db(db.Course.id == request.vars.cid).update(
                no_of_hta=No_of_Type - 1)
        else:
            No_of_Type = db(
                db.Course.id == request.vars.cid).select()[0].no_of_fta
            db(db.Course.id == request.vars.cid).update(
                no_of_fta=No_of_Type - 1)
        course = db(db.Course.id == request.vars.cid).select()[0]
        db.auth_event.insert(
            origin=session.student_email,
            user_type="student",
            description="rejected course " +
            course.cname,
            NAME=session.name,
            uid=session.roll)

        db(db.SelectedTA.appid == appid).delete()

        db((db.AppliedFor.appid == appid)).update(noflag='0')
        session.flash = 'Course rejected Successfully '
    redirect(URL(r=request, f='status'))


def accept_offer(appid):
    """
        Accepts the offered position to 'appid'
    """

    Id2 = db(db.SelectedTA.appid == appid).select()[0]
    if Id2:  # ----check if applicant is selected by Admin
        db(db.SelectedTA.appid == appid).update(flag=1)
        course = db(db.Course.id == request.vars.cid).select()[0]
        c = db(db.logs.cname == course.cname).select(db.logs.id)[0]
        Courses = db(db.Course.id == course.id).select(db.Course.cname)
        for i in Courses:
            courses = i.cname
        x = ""
        t = datetime.datetime.now()
        if t.month < 7:
            x = str(t.year) + " " + "Spring"
        else:
            x = str(t.year) + " " + "Monsoon"
        query = db(
            (db.ta_records.cname == courses) & (
                db.ta_records.time == x)).select(
            db.ta_records.id)
        flag_c = 0
        entry = 0
        for i in query:
            entry = i.id
        qu = db(db.Applicant.id == appid).select(db.Applicant.aprollno)
        ROLL = 0
        for i in qu:
            ROLL = i.aprollno
        if entry > 0:
            flag_c = 1

        if flag_c == 1:
            q = db(
                db.ta_records.cname == courses).select(
                db.ta_records.No_of_TAs)
            p = q[0].No_of_TAs
            p += 1
            db(db.ta_records.id == entry).update(No_of_TAs=p)
            db.ta_applicant.insert(
                ta_id=entry,
                applicant_id=ROLL,
                applicant_name=session.name,
                applicantid=session.student_email)
        else:
            q = db(db.Course.cname == courses).select(db.Course.cid)
            for i in q:
                cd = i.cid
            db.ta_records.insert(time=x, cname=courses, cid=cd, No_of_TAs=1)
            query = db(db.ta_records.cname == courses).select(db.ta_records.id)
            for i in query:
                entry = i.id
            db.ta_applicant.insert(
                ta_id=entry,
                applicant_id=ROLL,
                applicant_name=session.name,
                applicantid=session.student_email)
        db((db.logs_applicant.applicantid == session.student_email) &
           (db.logs_applicant.logid == c.id)).update(Status='Accepted')
        db.auth_event.insert(
            origin=session.student_email,
            user_type="student",
            description="accepted course " +
            course.cname,
            name=session.name,
            uid=session.roll)
    session.flash = 'Get your TA reporting form from "TA Reporting Form" button in menu bar'
    redirect(URL(r=request, f='status'))
#-------------------------------------------------------------------------------
def student_profile():
    """
        Method to show student profile which includes :
        1. Name
        2. Roll No
        3. Email
        4. Phone Number
        5. CGPA
        6. Previous Experience
    """
    if (session.role != 2):
        redirect(URL(r=request, f='index'))
        return dict()
    student_details = db(
        (db.Applicant.apemail_id == session.student_email) & (
            db.Applicant.program_id == db.Program.id)).select()
    return dict(records=student_details)




def isas_upload():
    if(session.role != user_roles["admin"]):
        redirect(URL(r=request,f='index'))
        return dict()
    form = crud.create(db.isas_upload)
    if form.accepts(request.vars,session) :
        r=db(db.isas_upload.id>0).select()
        k=r[len(r)-1]
        k=k.file.split('.')[2:]
        k='.'.join(k)
        db.auth_event.insert(origin=session.username,user_type="admin", description="uploaded file "+k,name=session.name,uid=session.roll)
        i=r[len(r)-1]
        filename=os.path.join(request.folder,'uploads',i.file)
        f=open(filename)
        for lines in f.readlines():
            lines=lines.strip('\n\r')
            list=lines.split(',')
            test = db(db.Applicant.aprollno==list[1].strip()).select().first()
            if( not( test )):
                db.Applicant.insert(apname=list[0].strip(),aprollno=list[1].strip(),apcgpa=list[2].strip())
#            elif (not db(db.SelectedTA.id == test.id).select()):
#                test.apemail_id = list[2].strip()
#                test.apname = list[0].strip()
#                test.apcgpa = list[3].strip()
#                test.update_record()
    return dict(form=form)

def minta():
    if(session.role != user_roles["admin"]):
        redirect(URL(r=request,f='index'))
        return dict()
    form = crud.create(db.isas_upload)
    if form.accepts(request.vars,session) :
        r=db(db.isas_upload.id>0).select()
        k=r[len(r)-1]
        k=k.file.split('.')[2:]
        k='.'.join(k)
        db.auth_event.insert(origin=session.username,user_type="admin", description="uploaded file "+k,name=session.name,uid=session.roll)
        i=r[len(r)-1]
        filename=os.path.join(request.folder,'uploads',i.file)
        f=open(filename)
        for lines in f.readlines():
            lines=lines.strip('\n\r')
            list=lines.split(',')
            test = db(db.Course.cid==list[1].strip()).select().first()
            if(test):
                test.no_of_ta = list[3].strip()
                test.update_record()
    return dict(form=form)

def course_list():
        r=''
        form = FORM(INPUT(_type="submit",_value="SUBMIT"))
        if form.accepts(request.vars,formname='confirm'):
                if request.vars['applicantId']=="Ta_couses":
                        r=db((db.AppliedFor.cid==db.Course.id) & (db.AppliedFor.appid == db.Applicant.id) &(db.AppliedFor.status!="None")).select(db.Course.cname,db.AppliedFor.preference,db.Applicant.apname,db.AppliedFor.status,db.AppliedFor.grade,db.Applicant.apcgpa)
                        session.r=r
                        redirect(URL(r = request, f = 'course_lists'))
                if request.vars['applicantId']=="Ta_couses1":
                        r=db((db.AppliedFor.cid==db.Course.id) & (db.AppliedFor.appid == db.Applicant.id)).select(db.Applicant.apname,db.AppliedFor.preference,db.Course.cname,db.AppliedFor.status,db.AppliedFor.grade,db.Applicant.apcgpa,orderby=db.Applicant.apname|db.AppliedFor.preference)
                        session.r=r
                        redirect(URL(r = request, f = 'course_lists1'))
        return dict(form=form)

def course_lists():
        return dict(r=session.r)

def course_lists1():
        return dict(r=session.r)

def feedback_upload():
    if(session.role != user_roles["admin"]):
        redirect(URL(r=request,f='index'))
        return dict()
    form = crud.create(db.feedback_upload)
    if form.accepts(request.vars,session) :
        r=db(db.feedback_upload.id>0).select()
        k=r[len(r)-1]
        k=k.file.split('.')[2:]
        k='.'.join(k)
        db.auth_event.insert(origin=session.username,user_type="admin", description="uploaded file "+k,name=session.name,uid=session.roll)
        i=r[len(r)-1]
        filename=os.path.join(request.folder,'uploads',i.file)
        f=open(filename)
        for lines in f.readlines():
            lines=lines.strip('\n\r')
            list=lines.split(';')
            if( not( db((db.Feedback.s_id==list[1].strip()) & (db.Feedback.course_id==list[2].strip())).select())):
                db.Feedback.insert(s_id=list[1].strip(),course_id=list[2].strip(),rating=list[3].strip(),course_name=list[4].strip(),Comments=list[6].strip(),time=list[5].strip())
    return dict(form=form)

#----------- FUNCTIONALITY FOR ADMIN -------------------------------------------
def getPdf():
    # checking whether user is student or not
    checkIsStudent()

    title = "TA allocation form"
    title1 ="International Institute of Information Technology, Hyderabad"
    text = PDFBuilder.makeStringForPdf()
    text=text.split(",")
    styles = getSampleStyleSheet()
    #styles.add(ParagraphStyle(name='Table Top Black Back', fontName ='Helvetica',fontSize=14, leading=16,backColor = colors.black, textColor=colors.white, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='Top', alignment=TA_CENTER, fontSize=16 , fontName ='Helvetica'))
    styles.add(ParagraphStyle(name='Info', alignment=TA_CENTER, fontSize=14 , fontName ='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Info2', alignment=TA_RIGHT, fontSize=10 , fontName ='Helvetica'))
    styles.add(ParagraphStyle(name='Info3', alignment=TA_LEFT, fontSize=10 , fontName ='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Info4', alignment=TA_RIGHT, fontSize=10 , fontName ='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Info5', alignment=TA_LEFT, fontSize=10 , fontName ='Helvetica'))
    tmpfilename=os.path.join(request.folder,'private',str(uuid4()))
    doc = SimpleDocTemplate(tmpfilename)
    taappform=[]
    taappform.append(Paragraph(escape(title1),styles["Top"]))
    taappform.append(Spacer(2,0.1*inch))
    taappform.append(Paragraph("(Deemed University) ",styles["Top"]))
    taappform.append(Spacer(2,0.3*inch))
    taappform.append(Paragraph("""<u>TA Reporting Form for Monsoon / Spring </u> """,styles["Info"]))
    taappform.append(Spacer(2,0.3*inch))
    name=text[0][17:]
    for line in text:        
        line=line.split("\n")
        for  bit in line :
            taappform.append(Paragraph(escape(bit),styles["Normal"]))
        taappform.append(Spacer(2,0.3*inch))
    taappform.append(Paragraph("Signature of the Advisor",styles["Info3"]))
    taappform.append(Spacer(1,0.1*inch))
    taappform.append(Paragraph("(if you have any other form of assistance)",styles["Info5"]))
    taappform.append(Spacer(1,0.1*inch))
    taappform.append(Paragraph("Signature of the Student",styles["Info4"]))
    taappform.append(Spacer(2,0.4*inch))
    taappform.append(Paragraph("Signature of the Chair-TA ship Committee",styles["Info3"]))
    taappform.append(Spacer(2,0.5*inch))
    taappform.append(Paragraph("Signature of the Faculty",styles["Info3"]))
    taappform.append(PageBreak())
    taappform.append(Paragraph(escape(title1),styles["Top"]))
    taappform.append(Spacer(2,0.1*inch))
    taappform.append(Paragraph("(Deemed University) ",styles["Top"]))
    taappform.append(Spacer(2,0.3*inch))
    taappform.append(Paragraph("""<u>Teaching Assistant's Undertaking Form</u> """,styles["Info"]))
    taappform.append(Spacer(2,0.3*inch))
    
    taappform.append(Paragraph("I " +"""<u><b> """+name+""" </u></b>"""+ "hereby declare that as a Teaching Assistant I will fulfill the following duties assigned to me.",styles["Normal"]))
    taappform.append(Spacer(2,0.2*inch))
    taappform.append(Paragraph(" &nbsp&nbsp&nbsp 1. Conduct of tutorial class regularly (one class per week) and maintenance of attendance records to the tutorial classes.",styles["Normal"]))
    taappform.append(Paragraph(" &nbsp&nbsp&nbsp 2. Meeting the faculty once in a week to give feedback of the tutorial class and submission of attendance sheets. ",styles["Normal"]))
    taappform.append(Paragraph(" &nbsp&nbsp&nbsp 3. Evaluation of Mid Sem / End Sem answer scripts and submission of marks to the faculty within one week after the last day of concernced examinations. ",styles["Normal"]))
    taappform.append(Paragraph(" &nbsp&nbsp&nbsp 4. Evaluation of Quiz / surprise tests etc., and submission of marks to the faculty within a week's time of the conduct of the said test / Quiz. ",styles["Normal"]))
    taappform.append(Spacer(2,0.2*inch))
    taappform.append(Paragraph(" Note: For programming assignments or assignments on which students spend tremendous amount of time, the TA's should not set the deadline of submission after 9:00 PM (Monday to Friday) and on Saturdays and Sundays. ",styles["Info3"]))
    taappform.append(Spacer(2,0.2*inch))
    taappform.append(Paragraph(" &nbsp&nbsp&nbsp&nbsp TA ship duties are an important part in effective running of the academic programmes of the Institute. I have read and I understood that if I do not perform my duties as TA properly, I can be penalized through fines, and other disciplinary action such as noting of this fact on my transcript. ",styles["Normal"]))
    taappform.append(Spacer(2,0.3*inch))
    course=text[4][10:]
    taappform.append(Paragraph("Course: "+course,styles["Info3"]))
    taappform.append(Paragraph("TA's Signature",styles["Info4"]))
    taappform.append(Spacer(2,0.3*inch))
    taappform.append(Paragraph("Faculty: ",styles["Info3"]))
    taappform.append(Paragraph("Faculty's Signature",styles["Info4"]))
    for fname in fac:
        taappform.append(Paragraph(" &nbsp&nbsp "+fname.fname,styles["Normal"]))
        taappform.append(Spacer(2,0.1*inch))
    taappform.append(Spacer(2,0.3*inch))
    taappform.append(Paragraph("Date: ",styles["Info3"]))
    
    doc.build(taappform)
    data = open(tmpfilename,"rb").read()
    os.unlink(tmpfilename)
    response.headers['Content-Type']='application/pdf'
    return data
#------------------modified by Team 26------------------------------------------
def add_courses():
    if (session.role != user_roles["admin"]) :
        redirect(URL(r = request, f = 'index'))
        return dict()

#------------------  CREATING FORM FOR THE NEW COURSE --------------------------
#-----------used to get course information--------------------------------------
    form = form_factory(
        SQLField('Cname', 'string', label = 'Course Name', requires = IS_NOT_EMPTY(error_message = T('fill this'))),
        SQLField('Cid', 'string', label = 'Course Id', requires = IS_NOT_EMPTY(error_message = T('fill this'))),
        SQLField('Cofferto', label = 'Course Offered To', requires = IS_IN_DB(db, 'Program.id', '%(pname)s')),
        SQLField('No_of_credits', 'integer', label = 'No Of Credits', requires = IS_NOT_EMPTY(error_message = T('fill this'))),
        SQLField('No_of_Hours', label = 'No. Of Hours Per Week',requires=IS_NOT_EMPTY()),
        SQLField('No_of_Faculty', label = 'No. Of Faculty',requires=IS_NOT_EMPTY()),
        SQLField('No_of_TA', label = "No. Of TA'S",requires=IS_NOT_EMPTY()),
        SQLField('coursetype', 'string', label = 'Type Of Course', requires = IS_IN_SET(['Full','Half'])),
        SQLField('semester', label = 'Semester', requires = IS_IN_DB(db, 'Semester.id', '%(semname)s')))


    if form.accepts(request.vars, session):
        # STORING THE ENTERED VALUES IN VARIABLES 
        session.cname = request.vars.Cname
        session.cid = request.vars.Cid
        session.cofferto = request.vars.Cofferto
        session.no_of_ta=request.vars.No_of_TA
        session.no_of_faculty=request.vars.No_of_Faculty
        session.cdts = request.vars.No_of_credits
        session.ctype = request.vars.coursetype
        session.semid = request.vars.semester
        session.hours = request.vars.No_of_Hours
        redirect(URL(r = request, f = 'add_courses1'))
    return dict(form=form)
#-------------------------------------------------------------------------------
def view_previous_applicant_l():
    x=request.args(0)
    x=x.split('_')
    x=x[0]+' '+x[1]
    if(session.role != user_roles["admin"]):
        redirect(URL(r=request,f='index'))
        return dict()

    q=db((db.logs.id>0) & (db.logs.time==x)).select()
    return dict(q=q)

def ta_records():
    x=request.args(0)
    x=x.split('_')
    x=x[0]+' '+x[1]
    if(session.role != user_roles["admin"]):
        redirect(URL(r=request,f='index'))
        return dict()
    q=db((db.ta_records.id>0) & (db.ta_records.time==x)).select()
    return dict(q=q)

def view_previous_applicant_log():
    if(session.role != user_roles["admin"]):
        redirect(URL(r=request,f='index'))
        return dict()
    p=db(db.logs.id>0).select(db.logs.time)
    l=[]
    for i in p:
        l.append(i['time'])
    l=set(l)
    return dict(l=l)

def ta_dates():
    if(session.role != user_roles["admin"]):
        redirect(URL(r=request,f='index'))
        return dict()
    p=db(db.ta_records.id>0).select(db.ta_records.time)
    l=[]
    for i in p:
        l.append(i['time'])
    l=set(l)
    return dict(l=l)


def detail_view():
    if(session.role != user_roles["admin"]):
        redirect(URL(r=request,f='index'))
        return dict()
    q=request.args(0)
    l=db(db.logs_applicant.logid==q).select()
    return dict(l=l)

def ta_detail_view():
    if(session.role != user_roles["admin"]):
        redirect(URL(r=request,f='index'))
        return dict()
    q=request.args(0)
    l=db(db.ta_applicant.ta_id==q).select()
    return dict(l=l)
#-----used to get faculties details after add_courses and insert records in database

def add_courses1():
    
    cname = session.cname
    cid = session.cid
    cofferto = session.cofferto
    cdts = session.cdts
    ctype = session.ctype
    semid = session.semid
    hours = session.hours
    nof= int(session.no_of_faculty)
    nota=session.no_of_ta
    if request.vars.submit :
        profname = request.vars.prof_name
        profemail = request.vars.prof_email
        if nof==1:
            if(profname==None or profemail==None or profname=='' or profemail==''):
                session.flash="Fill All Fields"
                redirect(URL(r = request, f = 'add_courses1'))

        else:
            for i in range(0,int(nof)):
                if(profname[i]==None or profemail[i]==None or profname[i]=='' or profemail[i]==''):
                    session.flash="Fill All Fields"
                    redirect(URL(r = request, f = 'add_courses1'))

        r = db(db.Course.cid == cid).select() 
        if(r):                 # if course is already there in the database
            a = 1
            for i in r:
                use_id = i.id                               # if yes then  use_id <= Course.id of that course
        else:                                       # else insert that course                       
            db.auth_event.insert(origin=session.username,user_type="admin",description="added course "+cname,name=session.name,uid=session.roll)
            use_id = db.Course.insert(cid = cid, cname = cname, cdts = cdts,\
            no_of_ta = nota,no_of_qta = 0, no_of_hta = 0, no_of_fta = 0, coursetype = ctype, sem_id = semid, hours_per_week = hours,no_of_faculty=nof)
        if nof==1 :
            s = db(db.Faculty.femail_id == profemail).select()
            #if profname!="":
            db.auth_event.insert(origin=session.username,user_type="admin",description="added faculty "+ profname+" for course "+cname,name=session.name,uid=session.roll) 
                   
            if(s):                                      # if faculty is already present in the database
                for row in s:
                    newprof_id = row.id                                 # if yes then newprof_if <= Faculty.id of that faculty          
            else:
                newprof_id = db.Faculty.insert(fname = profname, femail_id = profemail)     # else insert that faculty
      
            k = db((db.Teach.faculty_id == newprof_id) & (db.Teach.course_id == use_id)).select()
            if(k):                                      # if both of them are present in TEACH table do nothing     
                a = 1
            else:           # else insert   
                db.Teach.insert(faculty_id = newprof_id, course_id = use_id)
        else:
            for i in range(0,int(nof)):
                s = db(db.Faculty.femail_id == profemail[i]).select()
                #if profname[i]!="":
                db.auth_event.insert(origin=session.username,user_type="admin",description="added faculty "+ profname[i]+" for course "+cname,name=session.name,uid=session.roll)   
                if(s):                                      # if faculty is already present in the database
                    for row in s:
                        newprof_id = row.id                                 # if yes then newprof_if <= Faculty.id of that faculty          
                else:
                    newprof_id = db.Faculty.insert(fname = profname[i], femail_id = profemail[i])       # else insert that faculty
        
                k = db((db.Teach.faculty_id == newprof_id) & (db.Teach.course_id == use_id)).select()
                if(k):                                      # if both of them are present in TEACH table do nothing     
                    a = 1
                else:           # else insert   
                    db.Teach.insert(faculty_id = newprof_id, course_id = use_id)
       
        session.flash = "Course Successfully added !!!"
       
        offer = db((db.OfferedTo.cid == use_id) & (db.OfferedTo.programid == cofferto)).select()    # insert in OfferedTo table
        if(offer):
            a = 1
        else:
            db.OfferedTo.insert(cid = use_id, programid = cofferto)
        redirect(URL(r = request, f = 'add_courses'))
    return dict(nof=nof)
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def add_faculty():
    if session.role != user_roles["admin"]:                      # -------- check if admin has logged in or not -------------------
        redirect(URL(r = request, f = 'index'))
        return dict()
    form=form_factory(
              SQLField('course',label="Select Course ",requires=IS_IN_DB(db,'Course.id','%(cname)s (%(cid)s )')),
              SQLField('Faculty_name',label="Faculty name",requires=IS_NOT_EMPTY()),
              SQLField('Faculty_email',label="Faculty email-id",requires=IS_NOT_EMPTY()))
    if form.accepts(request.vars,session):
        course=request.vars.course 
        profname=request.vars.Faculty_name
        profemail=request.vars.Faculty_email
        s = db(db.Faculty.femail_id == profemail).select()    
        if(s):                                      # if faculty is already present in the database
            for row in s:
                newprof_id = row.id                                 # if yes then newprof_if <= Faculty.id of that faculty          
        else:
            newprof_id = db.Faculty.insert(fname = profname, femail_id = profemail)     # else insert that faculty
        k = db((db.Teach.faculty_id == newprof_id) & (db.Teach.course_id == course)).select()
        if(k):                                      # if both of them are present in TEACH table do nothing     
            pass
        else:           # else insert   
            db.Teach.insert(faculty_id = newprof_id, course_id = course)
            nof=db(db.Course.id==course).select(db.Course.no_of_faculty)[0]
            db(db.Course.id==course).update(no_of_faculty=nof.no_of_faculty+1)   #----increasing the count of faculty of a course by 1---
        c=db(db.Course.id==course).select()[0]
        #if profname!="":
        db.auth_event.insert(origin=session.username,user_type="admin",description="added faculty "+profname+" to course "+c.cname,name=session.name,uid=session.roll)
        session.flash = 'Faculty Successfully Added'
        redirect(URL(r = request, f = 'add_faculty'))
    return dict(form=form)
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def add_program():
    if session.role != user_roles["admin"]:                      # -------- check if admin has logged in or not -------------------
        redirect(URL(r = request, f = 'index'))
        return dict()
    form=form_factory(
              SQLField('course',label="Select Course ",requires=IS_IN_DB(db,'Course.id','%(cname)s (%(cid)s )')),
              SQLField('program',label="Program",requires=IS_IN_DB(db,'Program.id','%(pname)s')))
    if form.accepts(request.vars,session):
        course=request.vars.course   
        program=request.vars.program
        offer = db((db.OfferedTo.cid == course) & (db.OfferedTo.programid == program)).select()    
        if(offer):               # -------if both of them are present in TEACH table do nothing------
            pass
        else:
            db.OfferedTo.insert(cid = course, programid = program)    #---- insert in OfferedTo table------
        c=db(db.Course.id==course).select()[0]
        p=db(db.Program.id==program).select()[0]
        db.auth_event.insert(origin=session.username,user_type="admin",description="added program "+p.pname+" to course "+c.cname,name=session.name,uid=session.roll)
        session.flash = 'Program Successfully Added'
        redirect(URL(r = request, f = 'add_program'))
    return dict(form=form)
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def update_course():
    if session.role != user_roles["admin"]:                      # -------- check if admin has logged in or not -------------------
        redirect(URL(r = request, f = 'index'))
        return dict()
    session.admin_varCid=""
    records = ""
    form34 =form_factory(SQLField('course', label = "Select Course ", requires = IS_IN_DB(db, 'Course.id', '%(cname)s ( %(cid)s )')))
                
    if form34.accepts(request.vars,session):
        session.admin_varCid=request.vars.course
        records = db(db.Course.id==session.admin_varCid).select()
    if(records):
            records=records[0]
   
    return dict(records=records,form34=form34)

#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------

def delete():
    if session.role != user_roles["admin"]:                      # -------- check if admin has logged in or not -------------------
        redirect(URL(r = request, f = 'index'))
        return dict()
    course =db(db.Course.id>0).select()
    if request.vars.submit:
        session.courseid=request.vars.cid
        if request.vars.confirm=='yes':         #-----checks if user have confirm the deletion
            if request.vars.submit=='Del_Course':
                c=db(db.Course.id==session.courseid).select()[0]
                db.auth_event.insert(origin=session.username,user_type="admin",description="deleted course "+c.cname,name=session.name,uid=session.roll)
                db(db.AppliedFor.cid == session.courseid).delete()
                db(db.Course.id == session.courseid).delete()
                db(db.SelectedTA.cid == session.courseid).delete()
                db(db.OfferedTo.cid == session.courseid).delete()
                db(db.Teach.course_id == session.courseid).delete()
                session.flash = 'Course Successfully Deleted'
                redirect(URL(r = request, f = 'delete'))    
        elif request.vars.submit=='Del_Faculty':
            redirect(URL(r = request, f ='delete_faculty'))
        elif request.vars.submit=='Del_Program':
            redirect(URL(r = request, f = 'delete_program'))
    return dict(course=course)    
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
def delete_faculty():
    if session.role != user_roles["admin"]:                      # -------- check if admin has logged in or not -------------------
        redirect(URL(r = request, f = 'index'))
        return dict()
    fname=db((db.Teach.course_id==session.courseid)&(db.Teach.faculty_id==db.Faculty.id)).select()
    if request.vars.submit:
        faculty_name=db((db.Faculty.id==db.Teach.faculty_id) & (db.Teach.id == request.vars.fid)).select()[0]
        c=db(db.Course.id==session.courseid).select()[0]       
        db.auth_event.insert(origin=session.username,user_type="admin",description="deleted faculty "+faculty_name.Faculty.fname+" for course "+c.cname,name=session.name,uid=session.roll)
        db(db.Teach.id == request.vars.fid).delete()
        nof=db(db.Course.id==session.courseid).select(db.Course.no_of_faculty)[0]
        db(db.Course.id==session.courseid).update(no_of_faculty=nof.no_of_faculty-1)   #----decreasing the count of faculty of a course by 1---
        if (db(db.Teach.course_id == session.courseid).count() == 0) :
            db(db.AppliedFor.cid == session.courseid).delete()
            db(db.Course.id == session.courseid).delete()
            db(db.SelectedTA.cid == session.courseid).delete()
            db(db.OfferedTo.cid == session.courseid).delete()
            session.flash = 'Course Successfully Deleted'
            redirect(URL(r = request, f = 'delete'))
        session.flash = 'Faculty Successfully Deleted'  
        redirect(URL(r = request, f = 'delete_faculty'))
    return dict(fname=fname)
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
def delete_program():
    if session.role != user_roles["admin"]:                      # -------- check if admin has logged in or not -------------------
        redirect(URL(r = request, f = 'index'))
        return dict()

    program=db((db.OfferedTo.cid==session.courseid)&(db.OfferedTo.programid==db.Program.id)).select()
    if request.vars.submit:
        c=db(db.Course.id==session.courseid).select()[0]
        program=db(db.Program.id==request.vars.pid).select()[0]
        db.auth_event.insert(origin=session.username,user_type="admin",description="deleted program "+program.pname+" for course "+c.cname,name=session.name,uid=session.roll)
        db(db.OfferedTo.id == request.vars.pid).delete()
        if (db(db.OfferedTo.cid == session.courseid).count() == 0) :
            db(db.AppliedFor.cid == session.courseid).delete()
            db(db.Course.id == session.courseid).delete()
            db(db.SelectedTA.cid == session.courseid).delete()
            db(db.Teach.course_id == session.courseid).delete()
            session.flash = 'Course Successfully Deleted'
            redirect(URL(r = request, f = 'delete'))
        session.flash = 'Program Successfully Deleted'
        redirect(URL(r = request, f = 'delete_program'))
    return dict(program=program)
#-------------------------------------------------------------------------------

#-------------------------NOT IN USE--------------------------------------------
def delete_courses():
    if session.role != user_roles["admin"]:                      # -------- check if admin has logged in or not -------------------
        redirect(URL(r = request, f = 'index'))
        return dict()

    form = form_factory(                        # -------- creating form for the delete course --------------           
          SQLField('course', label = 'Select Course  ', requires = IS_IN_DB(db, 'Course.id', '%(cname)s  ( %(cid)s ) ' )),
          SQLField('cofferto', label = 'Select Program ', requires = IS_IN_DB(db, 'Program.id', '%(pname)s')))
    return dict(form=form)
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Allows Admin to see detail of Applicant
def applicant_profile():
    if session.role != user_roles["admin"]:
        redirect(URL(r=request, f='index'))
        return dict()
    records = db((db.Applicant.apemail_id == request.args(0)) & (db.Applicant.program_id == db.Program.id)).select()
    return dict(records = records )
#-------------------------------------------------------------------------------         


#-------------------------------------------------------------------------------
def namewise_list():
# ALLOWS ADMIN TO SEE THE APPLICANT LIST NAMEWISE 
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()

    r = ''
# form for select the applicant name 
    form = form_factory(    
          SQLField('applicantId', label = 'Select Applicant', requires = IS_IN_DB(db, 'Applicant.id',\
            '%(apname)s (%(aprollno)s)')))
    if form.accepts(request.vars, session):
        r = db((db.Applicant.id == db.AppliedFor.appid) & (db.Course.id == db.AppliedFor.cid) &\
            (db.Applicant.id == request.vars.applicantId)).select()
    return dict(form = form, msg = r)
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
#------------------ ALLOWS ADMIN TO SEE THE LIST OF SELECTED APPLICANTS CATEGORY WISE eg: NAME, COURSE, ROLLNO etc.......-------------------
def selected_TA():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    return dict()
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
def course_selected_ta():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    id2 =  request.args(0)
    return dict(id2=id2)   

#-------------------------------------------------------------------------------


#-------------------------------------------------------------------------------
def update_ta():
    a=0
    r= db(db.Course.id > 0).select()
    for i in r:
       
        quater=db((db.SelectedTA.cid==i.id)&(db.SelectedTA.TAtype=="quarter")).count()
        half=db((db.SelectedTA.cid==i.id)&(db.SelectedTA.TAtype=="half")).count()
        full=db((db.SelectedTA.cid==i.id)&(db.SelectedTA.TAtype=="full")).count()
        db(db.Course.id == i.id).update(no_of_qta = quater )
        db(db.Course.id == i.id).update(no_of_hta = half)
        db(db.Course.id == i.id).update(no_of_fta = full)
        a=a+half+full+quater
    
    response.flash = "%d records modified" % a
    return dict()
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def sel_course():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()

    form = form_factory(
            SQLField('course', label = 'Select Course  ', requires = IS_IN_DB(db, 'Course.id', '%(cname)s  ( %(cid)s ) ' )))
    if form.accepts(request.vars, session):
        redirect(URL(r = request, f = 'unselected_TA',args=[form.vars.course]))
    return dict(form=form)
#-------------------------------------------------------------------------------

def unselected_TA():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    formvars=""
    session.mark.clear()
    form = FORM(INPUT(_type="submit",_value="SUBMIT"))
    r = db((db.SelectedTA.cid==request.args[0])&(db.Course.id ==db.SelectedTA.cid)&(db.Applicant.id == db.SelectedTA.appid)).select(orderby = db.Course.id)
    courseId = request.args[0]
    for i in r:
        form.append(INPUT(_type="checkbox",_name=str(i.SelectedTA.id)))
    if form.accepts(request.vars, formname='confirm'):
        n = 0
        formvars=form.vars
        for i in r:
            applicantId = db(db.Applicant.aprollno == i.Applicant.aprollno).select()[0]
            if form.vars[str(i.SelectedTA.id)]=="on":
                c=db(db.Course.id==i.SelectedTA.cid).select()[0]
                db.auth_event.insert(origin=session.username,user_type="admin",description="unselected "+applicantId.apname+" for course "+c.cname,name=session.name,uid=session.roll)
                db((db.AppliedFor.appid == applicantId.id)).update(noflag = '0')
                db((db.AppliedFor.appid == applicantId.id) & (db.AppliedFor.cid==request.args[0])).update(status='None')
                db(db.SelectedTA.id == i.SelectedTA.id).delete()
                db(db.SelectedTA.id == i.SelectedTA.id).delete()
                if i.SelectedTA.TAtype=="quarter":
                    db(db.Course.id == i.SelectedTA.cid).update(no_of_qta = db.Course.no_of_qta - 1 )
                if i.SelectedTA.TAtype=="half":
                    db(db.Course.id == i.SelectedTA.cid).update(no_of_hta = db.Course.no_of_hta - 1 )
                if i.SelectedTA.TAtype=="full":
                    db(db.Course.id == i.SelectedTA.cid).update(no_of_fta = db.Course.no_of_fta - 1 )
                n += 1
        session.flash = "%d records modified" % n
        redirect(URL(r=request, args=courseId, f='unselected_TA'))
    return dict(r=r,form=form,formvars=formvars,courseId=courseId)


#----------------- DISPLAYS THE LIST OF APPLICANTS FOR A SELECTED COURSE -----------------------------------------------

def admin_applicant_list_2():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    if request.vars.suggest=="no":               #--------------if reset button is pressed
        session.p=""
    elif request.vars.suggest=="True":           #--------------if any attribute is pressed acc. to whichsorting is desired
        if session.p!="":
            session.p=session.p+ ',' + request.vars.s      #-------concat the new preference with old preference
        else:
            session.p=request.vars.s
    else: 
        if((not request.vars.submit) and  request.vars.submit!="No_list"):
            session.p=""
            if len(request.args):
                if session.admin_varCid != request.args(0):
                    session.mark.clear()
                session.admin_varCid=request.args(0)
        else:
            session.admin_varCid=""
            session.mark.clear()
    var=session.p
    records = db((db.AppliedFor.cid == session.admin_varCid) & (db.Applicant.id == db.AppliedFor.appid) & \
                                          (db.AppliedFor.cid==db.Course.id) & (db.Applicant.program_id == db.Program.id)).select(orderby=(var))
        
    form34 =form_factory(SQLField('course', label = "Select Course ", requires = IS_IN_DB(db, 'Course.id', '%(cname)s ( %(cid)s )',orderby='cname')))
                
    if form34.accepts(request.vars,session):
        session.admin_varCid=request.vars.course
        records = db((db.AppliedFor.cid == request.vars.course) & (db.Applicant.id == db.AppliedFor.appid) & \
                                       (db.AppliedFor.cid==db.Course.id) & (db.Applicant.program_id == db.Program.id)).select()
        session.mark.clear()
        redirect(URL(r = request, args = request.vars.course,f = 'admin_applicant_list_2'))
        session.p=""
    if session.admin_varCid!="":
        coursename=db((db.Course.id==session.admin_varCid)).select()[0].cname
    else:
        coursename=""
    return dict(records=records,form34=form34,coursename=coursename)

#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def admin_applicant_list_3():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    return dict()
#-------------------------------------------------------------------------------

#---------------------------function to set dates------------------------------- 
def set_date():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    check=db(db.Portaldate.id>0).select()
    if check:
        start=check[0].start_date
        end=check[0].end_date
    
    else :
        start=''
        end=''
    form=form_factory(
           SQLField('start', 'datetime', label = 'Start_date', requires = IS_NOT_EMPTY(error_message = T('fill this'))),
           SQLField('end', 'datetime', label = 'End_date', requires = IS_NOT_EMPTY(error_message = T('fill this'))))
    form.vars.start = start
    form.vars.end = end
    if form.accepts(request.vars,session):
        start = request.vars.start
        end = request.vars.end
        if check:
            db(db.Portaldate.id>0).update(start_date=start,end_date=end)
        else :    
            db.Portaldate.insert(start_date=start,end_date=end)
        db.auth_event.insert(origin=session.username,user_type="admin",description="set start date to "+start+" and end date to "+end,name=session.name,uid=session.roll)
        response.flash = "Date changed."
    return dict(form=form,start=start,end=end)
#-------------------------------------------------------------------------------
def nominate_date():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    check=db(db.Faculty_deadline.id>0).select()
    if check:
        start=check[0].start_date
        end=check[0].end_date
    
    else :
        start=''
        end=''
    form=form_factory(
           SQLField('start', 'datetime', label = 'Start_date', requires = IS_NOT_EMPTY(error_message = T('fill this'))),
           SQLField('end', 'datetime', label = 'End_date', requires = IS_NOT_EMPTY(error_message = T('fill this'))))
    form.vars.start = start
    form.vars.end = end
    if form.accepts(request.vars,session):
        start = request.vars.start
        end = request.vars.end
        if check:
            db(db.Faculty_deadline.id>0).update(start_date=start,end_date=end)
        else :    
            db.Faculty_deadline.insert(start_date=start,end_date=end)
        db.auth_event.insert(origin=session.username,user_type="admin",description="set faculty deadline start date to "+start+" and end date to "+end,name=session.name,uid=session.roll)
        response.flash = "Date changed."
    return dict(form=form,start=start,end=end)
#-------- FUNCTION FOR MAKING THE SUBJECT TO BE SENDED TO THE TAs --------------
def MakeStringForTA(course,sem, roll):
    admin = db(db.Admin.id > 0).select(db.Admin.ademail_id)[0]
    courseName = db(db.Course.cid == course).select()[0]
    string="Dear Student,\n\rYou Have been selected as " + session.admin_rollType[roll] + " TA for " + courseName.cname + '(' + course + ')' + \
          " for " + sem + " Semester. \n The following steps (in order) need to be taken for confirmation of TAship.\n" + "1. You should ACCEPT or REJECT the TA ship ONLY via the TA portal (taship.iiit.ac.in) with in 24 hrs of the receipt of this email.\n"+ "2. If you Accept TAship, you should get the TA form signed by the concerned faculty and the TA chair (in any order) and then submit the TA Report form in Academic office. \r\n\n\nTA Chair\r\nIIIT Hyderabad."

#    string = "You Have been selected as " + session.admin_rollType[roll] + " TA for " + courseName.cname + '(' + course + ')' + \
#          " for " + sem + " Semester. Please send your acceptance by sending a email to " + admin.ademail_id + ", and Please report to the concerned faculty and submit the TA Report form in Academic office.\r\n\n\nTA Chair\r\nIIIT Hyderabad."
    return string
#-------------------------------------------------------------------------------

#-------- FUNCTION FOR MAKING THE SUBJECT TO BE SENDED TO THE FACULTY ----------
def MakeStringForFaculty(course, courseId, list):
#    string = "Respected Faculty,\r\n\tPlease note that following applicants are selected as a TA :\r\n" + list + " for your course "\
#          + course + "(" + courseId + ").\r\n\nThank You\r\nTA Chair\r\nIIIT-Hyderabad"
    string = "Respected Faculty,\r\n\tPlease note that following applicants are selected as a TA for your course "\
          + course + "(" + courseId + ") :\r\n"+list+"\r\n\nThank You\r\nTA Chair\r\nIIIT-Hyderabad"
    return string
def MakeStringForad(course, courseId, list):
#    string = "Respected Faculty,\r\n\tPlease note that following applicants are selected as a TA :\r\n" + list + " for your course "\
#          + course + "(" + courseId + ").\r\n\nThank You\r\nTA Chair\r\nIIIT-Hyderabad"
    string = "Respected Admin,\r\n\tPlease note that following applicants are selected as a TA for your course "\
          + course + "(" + courseId + ") :\r\n"+list+"\r\n\nThank You\r\nTA Chair\r\nIIIT-Hyderabad"
    return string
#-------------------------------------------------------------------------------

#------- FUNCTION FOR SENDING MAIL BY THE ADMIN TO THE FACULTY AND TA'S --------
def admin_send_mail():
    msg=''
    if session.role != user_roles["admin"]:
            redirect(URL(r = request,f='index'))
            return dict()

    courseId = request.args[0]
    back = courseId
    course = db(db.Course.id == courseId).select()[0]
    courseId = db( (db.Course.id == courseId) & (db.Course.sem_id == db.Semester.id) & \
          (db.Course.id == db.Teach.course_id) & (db.Faculty.id == db.Teach.faculty_id )).select()[0]
    applicantList = session.admin_applicantList
    listForFacultyText = '\r\n'
    for roll in applicantList:
        record = db(db.Applicant.aprollno == roll).select()[0]
        listForFacultyText += 'Name: ' + record.apname + '\r\nTA Type: ' + session.admin_rollType[roll] + '\r\nRoll No.: ' +\
              str(record.aprollno) + '\r\nPhone No.: ' + str(record.phoneno) + '\r\nEmail-id: ' + record.apemail_id + '\r\n\n\n'
        sender = db(db.Admin.id > 0).select()[0]
        sender = sender.ademail_id
        reciever = record.apemail_id
        text = MakeStringForTA(course.cid, courseId.Semester.semname, roll)
        title =  'TA-Ship Selection for ' + courseId.Course.cname
        sendmail(sender, reciever, text, title)
    
    courseIdSame = db( (db.Course.id == courseId.Course.id) & (db.Course.sem_id == db.Semester.id) &\
          (db.Course.id == db.Teach.course_id) & (db.Faculty.id == db.Teach.faculty_id )).select()
    for emailId in courseIdSame:
        reciever = emailId.Faculty.femail_id
        text = MakeStringForFaculty(courseId.Course.cname, courseId.Course.cid, listForFacultyText)
        title = 'List of Selected TA' + "'s" + ' for ' + courseId.Course.cname + '(' + courseId.Course.cid + ')'
        sendmail(sender, reciever, text, title)
    text = MakeStringForad(courseId.Course.cname, courseId.Course.cid, listForFacultyText)
    returnValue1 = sendmail(sender, sender, text, title)
    if returnValue1 == 1:
        db.auth_event.insert(origin=sender,user_type="admin",description="mail sent to " + str(reciever),name=session.name,uid=session.roll)
        msg = 'Mail Sent successfully'
    else:
        msg = 'Mail Sending failed'
    return dict(msg=msg,courseId = back)
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def admin_allocatedTA():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()

    records = db(db.Course.id > 0).select()
    return dict(records=records)
#-------------------------------------------------------------------------------

#--------- ALLOWS ADMIN TO UPLOAD A FILE WHICH CONTAINS THE COURSE INFO --------
# -------------- AN ALTERNATE FOR THE ADD COURSES QUERY ------------------------

def upload():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    
    form = crud.create(db.Upload)
    
    if form.accepts(request.vars, session):
        response.flash = 'file uploaded'
        f=request.vars.file
        r = db(db.Upload.id > 0).select()
        k=r[len(r)-1]
        k=k.file.split('.')[2:]
        k='.'.join(k)
        db.auth_event.insert(origin=session.username,user_type="admin", description="uploaded file "+k,name=session.name,uid=session.roll)
        i=r[len(r)-1]
        filename = os.path.join(request.folder, 'uploads', i.file)
        f = open(filename)
        for lines in f.readlines():
            if len(lines) < 20:
                break
            lines = lines.strip('\n\r')
            list = lines.split(',')
            if( not( db(db.Course.cid == list[1].strip()).select() ) ):
                getCid = db.Course.insert(cname = list[0].strip(), cid = list[1].strip(),\
                cdts = list[2].strip(' '), no_of_ta = 10,no_of_qta = 0, no_of_hta = 0, no_of_fta = 0, \
                hours_per_week = 5, \
                sem_id = 1,\
                coursetype = list[3].strip(),\
                no_of_faculty=list[4].strip())
            else:
                getCid = db(db.Course.cid == list[1].strip()).select()[0].id
            for j in range(0,int(list[4])):
                if( not( db(db.Faculty.femail_id == list[6+2*j].strip()).select() ) ):
                    getPid = db.Faculty.insert(fname = list[5+2*j].strip(), femail_id = list[6+2*j].strip())
                else:
                    getPid = db(db.Faculty.femail_id == list[6+2*j].strip()).select()[0].id
                if( not(db((db.Teach.course_id == getCid) & (db.Teach.faculty_id == getPid)).select()) ):
                    db.Teach.insert(course_id = getCid, faculty_id = getPid)
    return dict(form=form)


def edit_max():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    id1 = request.args(0)
    records = db(db.Course.id==id1).select()
    if(records):
            records=records[0]
    return dict(records=records,course=db.Course.id)


#-------------------------------------------------------------------------------
#------------------ Admin Related queries ends here ----------------------------

#------------------ Faculty related queries ------------------------------------
#-------- ALLOWS FACULTY TO SEE THE APPLICANTS LIST FOR THE SELECTED COURSE ----
def faculty_applicant_list_2():
        
    if session.role != user_roles["faculty"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    if request.vars.suggest=="no":
        session.p=""
    elif request.vars.suggest=="True":
        if session.p!="":
            session.p=session.p+ ',' + request.vars.s
        else:
            session.p=request.vars.s
    else: 
        if((not request.vars.submit) and  request.vars.submit!="No_list"):
            session.p=""
            session.faculty_varCid=""
#        if(request.vars.submit=="No_List"):
#            session.flash=request.args[0]
#            session.course=request.args[0]
    var=session.p
    records = db((db.AppliedFor.cid == session.faculty_varCid) & (db.Applicant.id == db.AppliedFor.appid) & \
                                          (db.AppliedFor.cid==db.Course.id) & (db.Applicant.program_id == db.Program.id)).select(orderby=(var))
    form34 =form_factory(SQLField('course', label = "Select Course ", requires =\
                                                      IS_IN_DB(db((db.Faculty.femail_id == session.faculty_login_emailid)\
                                                     & (db.Teach.faculty_id == db.Faculty.id) & \
                                                  (db.Teach.course_id == db.Course.id)), 'Course.id', '%(cname)s ( %(cid)s )')))
    
    #form34 =form_factory(SQLField('course', label = "Select Course ", requires =\
    #                                                  IS_IN_DB(db((db.Faculty.femail_id == session.username)&(db.Teach.faculty_id == db.Faculty.id) & \
    #                                              (db.Teach.course_id == db.Course.id)), 'Course.id', '%(cname)s ( %(cid)s )')))

    if form34.accepts(request.vars,session):
        r=[]
        session.faculty_varCid=request.vars.course
        records = db((db.AppliedFor.cid == session.faculty_varCid) & (db.Applicant.id == db.AppliedFor.appid) & \
                                       (db.AppliedFor.cid==db.Course.id) & (db.Applicant.program_id == db.Program.id)).select()
       ##      records.append(r)
      #  else:
      #      records=r
    #print records
    flag=0
    if len(records)==1:
        flag=1
    session.p=""
    if session.faculty_varCid!="":
        coursename=db((db.Course.id==session.faculty_varCid)).select()[0].cname
    else:
        coursename=""
    return dict(flag=flag,form34=form34,records=records,coursename=coursename,courseid=session.faculty_varCid)
#-------------------------------------------------------------------------------


#-------------------------------------------------------------------------------
def faculty_applicant_list_3():
    if session.role != user_roles["faculty"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
    return dict()



#-------------------------------------------------------------------------------
def help():
    return dict(message=session.username)
#-------------------------------------------------------------------------------


#--------- RETURNS A STRING WHICH IS THE SUBJECT OF THE MAIL BELOW -------------
def MakeStringForAdmin(courseName, courseId, list, sem):
    string="I nominate \n" + list + "for " + courseName + "(" + courseId +") for " + sem + "."
    return string
#-------------------------------------------------------------------------------



#---- ALLOWS FACULTY TO SEND MAIL TO THE ADMIN FOR THE NOMINATIONS FOR THEIR COURSE --------------------------
def faculty_send_mail():
    msg=''
    if session.role != user_roles["faculty"]:
        redirect(URL(r = request, f = 'index'))
        return dict()

    courseId = request.args[0]
    course = db(db.Course.id == courseId).select()[0]
    courseId = db( (db.Course.id == courseId) & (db.Course.sem_id == db.Semester.id) &\
          (db.Course.id == db.Teach.course_id) & (db.Faculty.id == db.Teach.faculty_id )).select()[0]
    applicantList = session.faculty_applicantList
    listForAdminText = '\r\n'
    for roll in applicantList:
        record = db(db.Applicant.aprollno == roll).select()[0]
        listForAdminText += 'Name: '+ record.apname + '\r\nTA Type: ' + session.faculty_rollType[roll] + '\r\nRoll No.: ' + \
              str(record.aprollno) + '\r\nPhone No.: ' + str(record.phoneno) + '\r\nEmailid: ' + record.apemail_id + '\r\n\r\n'
    reciever_g = db(db.Admin.id > 0).select()[0]
    reciever_g = reciever_g.ademail_id
    reciever_k = db(db.Admin.id > 0).select()[2]
    reciever_k = reciever_k.ademail_id
    
    sender = courseId.Faculty.femail_id
    text = MakeStringForAdmin(courseId.Course.cname, courseId.Course.cid, listForAdminText, courseId.Semester.semname)
    title = 'TA-Ship Nominations for ' + courseId.Course.cname + '(' + courseId.Course.cid + ')'
    returnValue1 = sendmail(sender, reciever_k,  text, title)
    returnValue1 = sendmail(sender, reciever_g,  text, title)
    returnValue1 = 1
    if (returnValue1 == 1) :
        db.auth_event.insert(origin=sender,user_type="faculty",description="sent mail to" + str(reciever_g),name=session.name,uid=session.roll)
        msg = 'Mail Sent successfully'
    else:
        msg = 'Mail Sending failed'
    sendmail(sender, sender, text, title)
    return dict(msg=msg)
#-------------------------------------------------------------------------------

#-------- ALLOWS FACULTY TO SEE THE TAS ALLOCATED IN THEIR COURSES -------------
def faculty_allocatedTA():
    if session.role != user_roles["faculty"]:
        redirect(URL(r = request, f = 'index'))
        return dict()

    records = db((db.Faculty.id == db.Teach.faculty_id) & (db.Teach.course_id == db.Course.id) & \
          (db.Faculty.femail_id == session.faculty_login_emailid)).select()
    return dict(records=records)
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
def faculty_selectedTA():
    if session.role != user_roles["faculty"]:
        redirect(URL(r = request, f = 'index'))
        return dict()
#----------added (db.SelectedTA.flag==1) to select query to retrive applicant who have accepted the taship
    records = db((db.Faculty.id == db.Teach.faculty_id)  & (db.Teach.course_id == db.Course.id) & \
          (db.SelectedTA.appid == db.Applicant.id) & (db.SelectedTA.cid == db.Course.id) & \
          (db.Faculty.femail_id == session.faculty_login_emailid) & (db.AppliedFor.appid == db.Applicant.id) &\
          (db.AppliedFor.cid == db.Course.id)).select(orderby = 'cname')
    return dict(records=records)
#-------------------------------------------------------------------------------


def logtable():
    row=None
    
    form = form_factory(
            SQLField('email', 'string'),
            SQLField('date', 'date',requires=IS_EMPTY_OR(IS_DATE())),
            SQLField('user', requires=IS_EMPTY_OR(IS_IN_SET(['faculty','student','admin']))),
            SQLField('name','string'),
            SQLField('uid','string'))
                        
    if form.accepts(request,session):
             
        var1=form.vars.date
        var2=form.vars.email
        var3=form.vars.user
        var4=form.vars.name
        var5=form.vars.uid
        if var4==None:
            var4=''
        if var3==None:
            var3=''
        if (var1!=None) & (var5!='') :
            row=db( (db.auth_event.origin.regexp("%"+var2+"%")) & (db.auth_event.user_type.startswith(var3)) &
                 (db.auth_event.time_stamp.year()==var1.year) & (db.auth_event.time_stamp.month()==var1.month) & (db.auth_event.time_stamp.day()==var1.day) & (db.auth_event.name.like("%"+var4+"%")) & (db.auth_event.uid==var5)).select()

        elif (var1==None) & (var5!=''):

            row=db( (db.auth_event.origin.like("%"+var2+"%")) & (db.auth_event.user_type.startswith(var3)) &
                  (db.auth_event.name.like("%"+var4+"%")) & (db.auth_event.uid==var5)).select()
        elif (var1!=None) & (var5==''):

            row=db( (db.auth_event.origin.like("%"+var2+"%")) & (db.auth_event.user_type.startswith(var3)) &
                 (db.auth_event.time_stamp.year()==var1.year) & (db.auth_event.time_stamp.month()==var1.month) & (db.auth_event.time_stamp.day()==var1.day) & (db.auth_event.name.like("%"+var4+"%"))).select()
        else:

            row=db( (db.auth_event.origin.like("%"+var2+"%")) & (db.auth_event.user_type.startswith(var3)) & (db.auth_event.name.like("%"+var4+"%"))).select()
    return dict(form=form,row=row)
################################################################################
################################################################################
def index():

    session.role = user_roles["none"]
    session.LOGGEDIN = 0
    redirect(URL(r=request,f='login'))
    """
    example action using the internationalization operator T and flash
    rendered by views/default/index.html or views/generic.html
    """

    return dict(message=T('Hello World'))


def user():
    """
    exposes:
    http://..../[app]/default/user/login 
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    return dict(form=auth())


def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request,db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    session.forget()
    return service()





  #####################################################################################################################################
  # Sending mail to admins from contacts#
def admin_contact():
    sender=request.vars.sender
    reciever=request.vars.reciever
    subj=request.vars.subject
    title=request.vars.Content
    print sender
    print reciever
    print subj
    print title
    mail=NewMail()
    # specify server
    mail.settings.server='mail.iiit.ac.in:25'
    mail.settings.login='username:password' or None

# specify address to send as
    mail.settings.sender=sender

#   mail.settings.lock_keys=True
    mail.settings.use_tls=True
#       return mail.settings.keys()
#send the message
    print "Mail to be sent"
    a=mail.send(to=reciever, subject=subj, message=title)
    redirect(URL('contacts'))

#--------------------------------------------------------------------------

def notify():
    if(session.role == user_roles["admin"]):
        x=db(db.auth_event.description!="logged in").select()
        timelog_admin=[]
        for i in range(len(x)):
            if x[i].description!="logged out":
                timelog_admin.append(x[i])
        return dict(timelog_admin=timelog_admin)
    elif session.role == user_roles["faculty"]:
        x=db(db.Faculty.femail_id == session.username).select() #& db.Faculty.id == db.Teach.faculty_id & db.Teach.course_id == db.course.cid).select(db.Faculty.ALL, db.Teach.ALL, db.course.ALL)
        y=db(x[0].id == db.Teach.faculty_id).select()
        course=[]
        for i in range(len(y)):
            timelog=db(y[i].course_id == db.Course.id).select(db.Course.ALL)
            course.append(timelog[0].cname)
        timelog_course=[]
        for i in db().select(db.auth_event.ALL):
            for j in course:
                if re.findall(j,i.description):
                    timelog_course.append(i)
        return dict(timelog_course=timelog_course)
    elif session.role == user_roles["student"]:
        x=db(db.auth_event.origin == session.username).select()
        timelog_student=[]
        for i in range(len(x)):
            if ( x[i].description != "logged in"):
                if ( x[i].description != "logged out"):
                    timelog_student.append(x[i])
        return dict(timelog_student=timelog_student)

#--------------------------------------------------------------------------
def adminpriv():
    if session.role != user_roles["admin"]:
        redirect(URL(r = request , f = 'index'))
        return dict()
    
    return dict()

def about():
    return dict() 


def rem_dup():
    dupapp=db().select(db.Applicant.aprollno, having=db.Applicant.aprollno.count()>1, groupby = db.Applicant.aprollno)
    count=0;
    for app in dupapp:
        a=db(db.Applicant.aprollno==app.aprollno).select(db.Applicant.id)
        for b in a:
            c=db(db.AppliedFor.appid==b).select()
            if len(c)==0:
                db(db.Applicant.id==b).delete()
                count+=1;
                db.commit()
    return dict(r=count)


def edit_grade():
    # checking whether user is student or not
    checkIsStudent()

    appid=db(db.Applicant.apemail_id == session.student_email).select(db.Applicant.id)[0]
    appcor=db((db.AppliedFor.appid == appid)&(db.AppliedFor.cid==db.Course.id)&(db.AppliedFor.grade == None)).select()
    if(not len(appcor)):
            redirect(URL(r=request,f='home_page'))
            response.flash = "All courses updated sucessfully"
    form = form_factory(
               SQLField('course', label = 'Select Course '),
               SQLField('grade', label = 'Grade In The Course', requires = IS_IN_SET(['A','A-','B','B-','C','NA'])))
    grade_list = ['NA','A','A-','B','B-','C']
    return dict(form=form,appid=appid,appcor=appcor,grade_list=grade_list)

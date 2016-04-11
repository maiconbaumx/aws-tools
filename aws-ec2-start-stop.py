#ec2 shutdown after business hours and start on business hours
#run as python aws-ec2-start-stop.py <region> <inst_id1>,<inst_id2>,<inst_id3>
#Status code
# 0 (pending)
# 16 (running)
# 32 (shutting-down)
# 48 (terminated)
# 64 (stopping)
# 80 (stopped)
import boto.ec2
import sys
import time as t_time
from datetime import datetime, time, date

#business hours interval
start_business_hours = time(8,00)
end_business_hours = time(21,00)

#default variables
v_region=sys.argv[1]
now = datetime.now()
now_time = now.time()

def return_list_instances(ec2):
    vtag = {"tag:EC2_ECONOMIZATOR": "TRUE"}
    instances = ec2.get_only_instances(filters=vtag)
    return instances

def f_stop(ec2):
    list_instances = return_list_instances(ec2)
    for instances in list_instances:
        if instances.state_code == 16:
            print "The instance %s is in state %s and will be stopped" % (instances.id, instances.state)
            ec2.stop_instances(instances.id)
            t_time.sleep(3)
            instances.update()
            while instances.state_code in [64]:
                print "Wainting for stop of instance %s, current state %s" % (instances.id, instances.state)
                t_time.sleep(15)
                instances.update()
            if instances.state_code == 80:
                print "The instance %s is %s" % (instances.id, instances.state)
            else:
                print "ERROR: The instance %s is %s" % (instances.id, instances.state)
        elif instances.state_code == 80:
            print "The instance %s is already stopped." % instances.id
        else:
            print "ERROR: Instance %s status is %s." % (instances.id, instances.state)

def f_start(ec2):
    list_instances = return_list_instances(ec2)
    for instances in list_instances:
        if instances.state_code != 16:
            print "The instance %s is in state %s and will be started" % (instances.id, instances.state)
            ec2.start_instances(instances.id)
            t_time.sleep(3)
            instances.update()
            while instances.state_code in [0]:
                print "Wainting for start of instance %s, current state %s" % (instances.id, instances.state)
                t_time.sleep(15)
                instances.update()
            if instances.state_code == 16: 
                print "The instance %s is %s" % (instances.id, instances.state)
            else:
                print "ERROR: The instance %s is %s" % (instances.id, instances.state)
        elif instances.state_code == 16:
            print "The instance %s is already started." % instances.id
        else:
            print "ERROR: Instance %s status is %s." % (instances.id, instances.state)

ec2 = boto.ec2.connect_to_region(v_region)
if datetime.weekday(date.today()) in [5,6]:
    print "Not in a week day... stopping instances..."
    f_stop(ec2)
else:
    if now_time >= start_business_hours and now_time <= end_business_hours:
        print "Business hours OK - Starting instances"
        f_start(ec2)
    else:
        print "Business hours NOK - Stopping instances"
        f_stop(ec2)
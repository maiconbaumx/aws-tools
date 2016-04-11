#import modules
import boto.ec2, argparse, boto, os, sys, datetime, time, re
from collections import OrderedDict

#Parse parameters
parser = argparse.ArgumentParser(description='Tool to create and rotate EC2 AMIs and associated snapshots. \n \n \nUsage example: \n\nec2-backup.py -r us-east-1 -t Backup  -d 10 \nIn this example all EC2 from region us-east-1 with tag "Backup" = TRUE will have backups.', add_help=False, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-h', '--help', action='help', help='Show this help message and exit')
parser.add_argument('-t', '--tag', type=str, action='store', dest='tag', required=True, help='All EC2 with this TAG with value equals TRUE  - TAG:TRUE')
parser.add_argument('-r', '--region', type=str, action='store', dest='region', required=True, help='AWS region')
parser.add_argument('-d', '--days_of_retention', type=int, action='store', dest='ret', help='Days of retention for AMIs/Snapshots (default: 5 days )')
parser.add_argument('--reboot', action='store_false', dest='reboot', help='Reboot the instance to create the AMI (default: No reboot)')
parser.add_argument('--nodelete', action='store_true', dest='nodelete', help='Not remove the AMI/snapshots older than N days (default: delete after N days (-d))')
parser.add_argument('--nobackup', action='store_false', dest='nobackup', help='Not make the backup of AMI/snapshots. Use this to only remove old backups')

#usage print results.tag
results = parser.parse_args()

#if false reboot the ec2
noreboot=True
if results.reboot == False:
   noreboot=False
print "Flag de NO reboot is set to %s " % (noreboot)


#connect to aws
conn = boto.ec2.connect_to_region(results.region)
vtag={"tag:"+results.tag : "TRUE"}
#print "print vtag %s " % (vtag)

#create ami function

def create_ami():
   reservations= conn.get_all_instances(filters=vtag )
   instances = [i for r in reservations for i in r.instances]
   ami_ids=[]
   for i in instances:
       if i.state in ('running','pending', 'stopping', 'stopped'):
          now = datetime.datetime.now()
          v_inst=i.id
          v_imgname='Auto-backup-'+str(v_inst)+now.strftime("-%d-%m-%Y-%H-%M")
          print "Creating AMI to instance %s with the label %s" % (i.id,v_imgname)
    #AMI Tags
          ami_tags = {'Autobackup': "TRUE", 'Name' : v_imgname }
          new_id=conn.create_image(i.id, v_imgname, description="Autobackup", no_reboot=noreboot)
          print "New AMI ID is %s" % (new_id)
          time.sleep( 30 )
          conn.create_tags (new_id,ami_tags)
          ami_ids.append(new_id)
    #creating tags to snapshots from new ami
          create_snapshot_tags(ami_ids)
          
   return


def create_snapshot_tags(ami_id):
   ami_tags = {'Autobackup': "TRUE"}
   print "looking for snapshots... could take a while... "
   time.sleep(30)
   for am in ami_id:
      pattern = re.compile(am)
      for i in conn.get_all_snapshots():
         if str(pattern.search(i.description)) != 'None':
            conn.create_tags (i.id,ami_tags)
            print "Creating tags for snap id %s of ami id %s" % (i.id,am)
   return

#metodo criado para evidar duplicidade de codigo. Sera chamado mais de uma vez.
def delete_ami_snaps(ami_id):
    print "Deleting snapshots from AMI %s " % (ami_id)
    pattern = re.compile(ami_id)
    for i in conn.get_all_snapshots():
        if str(pattern.search(i.description)) != 'None':
            print "snapshots ID %s will be deleted as description: %s" % (i.id,i.description)
            conn.delete_snapshot(i.id)
            
def deregister_ami_snaps(ami_id): #metodo renomeado.Nome antigo era: delete_ami_snaps()
    rt=False
    try:
        rt=conn.deregister_image(ami_id)
        if rt == True: 
            delete_ami_snaps(ami_id)
    except Exception, e:
        if "InvalidAMIID" in e:
            delete_ami_snaps(ami_id)
        else:
            print e
               
    return

def check_amis():
   print "Checking for old snapshots to delete..."
   if results.ret is None:
      results.ret = 5
   print "Days of retention is %s" % (results.ret)
   vfilter={'tag:Autobackup': 'TRUE'}
   DATEFORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
   ret_time=datetime.datetime.now() - datetime.timedelta(days=results.ret)
   vlist=[]
   for i in conn.get_all_snapshots(filters=vfilter ):
      if datetime.datetime.strptime(i.start_time, DATEFORMAT) <= ret_time:
         vami=i.description.strip().split()
         vlist.append(vami[4])
   unique=[]

   if not vlist:
      print "Nothing to delete."
   else:
      [unique.append(item) for item in vlist if item not in unique]
      for i in unique:
         if results.nodelete is True:
            print "AMI ID %s was not deleted due parameter --nodelete" % (i)
         else:
            deregister_ami_snaps(i)
   return

# execution process

if results.nobackup is True:
   create_ami();
   check_amis();
else:
   print "Skip backup due parameter --nobackup"
   check_amis();
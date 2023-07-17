 
####################################################################
######          Copyright (c)  2022-2023 PGEDGE           #########
####################################################################

import platform, os, sys, subprocess, shutil
import util

arch = subprocess.check_output("arch")

platf = "unsupported"
if platform.system() == "Linux":
  if os.path.exists("/etc/redhat-release"):
    if arch == "aarch64":
      platf = "el9-arm"
    else:
      platf = "el9-amd"
  else:
    f = "/etc/os-release"
    if os.path.exists(f) and (arch == "x86_64"):
      with open(f,'r') as text_file:
        text_data = text_file.read()
        if text_data.find("22.04"):
          platf=ubu22-amd
elif platform.system() == "Darwin":
  platf = "osx"

if platf == "unsupported":
  util.message("nclibs not available for platform")
  sys.exit(0)

url  = util.get_value("GLOBAL", "REPO")
file = f"nclibs-{platf}.tar.bz2"

if util.download_file(url, file):
  if util.unpack_file(file):
    dir = "../hub/scripts/lib"
    shutil.move(platf, dir)
    sys.exit(0)

sys.exit(1)


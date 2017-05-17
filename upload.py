import os
import shutil
import subprocess
import zipfile
import imp

tdm_loader = imp.load_source('tdm_loader', 'C:\Users\Florian\PyCharmProjects\\tdm_loader\\tdm_loader\\tdm_loader.py')

current_dir = os.getcwd()
initial_files = os.listdir(current_dir)

with open(os.path.join(current_dir, 'README.txt'), 'w') as fobj:
    string = tdm_loader.__doc__
    fobj.write(string.replace('\n', '\r\n'))

cmd = 'python setup.py sdist bdist_egg bdist_wininst upload'
subprocess.check_call(cmd, shell=True)

cmd = 'make {0}'
subprocess.check_call(cmd.format('clean'), shell=True,
                      cwd=os.path.join(current_dir, 'docs'))
subprocess.check_call(cmd.format('html'), shell=True,
                      cwd=os.path.join(current_dir, 'docs'))

build_dir = os.path.join(current_dir, 'docs', 'build', 'html')
with zipfile.ZipFile('docs.zip', mode='w',
                     compression=zipfile.ZIP_DEFLATED) as zip_obj:
    for dirpath, dirnames, filenames in os.walk(build_dir):
        rel_dir = os.path.relpath(dirpath, build_dir)
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            archive_path = os.path.join(rel_dir, filename)
            zip_obj.write(file_path, archive_path)


initial_files.append('docs.zip')
all_files = os.listdir(current_dir)
for filename in all_files:
    file_path = os.path.join(current_dir, filename)
    if os.path.isfile(file_path) and filename not in initial_files:
        os.remove(file_path)
    if os.path.isdir(file_path) and filename not in initial_files:
        shutil.rmtree(file_path)

from pathmagic import Dir
import os
from miscutils import Profiler

testdir = Dir.from_home().newdir("test")
testdir.settings.lazy = True
run = 1000


print("pathmagic")

with Profiler() as magic_create_profiler:
    for num in range(run):
        testdir.newfile(f"test{num + 1}", "txt").write(f"Hi, I'm file number {num + 1}.")

print(magic_create_profiler)

with Profiler() as magic_delete_profiler:
    for file in testdir.files:
        file.delete()

print(magic_delete_profiler)


print("standard")

with Profiler() as standard_create_profiler:
    for num in range(run):
        with open(fR"{testdir}\test{num + 1}.txt", "w") as stream:
            stream.write(f"Hi, I'm file number {num + 1}.")

print(standard_create_profiler)

with Profiler() as standard_delete_profiler:
    for file in os.listdir(testdir):
        os.remove(f"{testdir}/{file}")

print(standard_delete_profiler)

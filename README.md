# yadda

Yet another dicom data actuator: Watches for dicoms in a directory, sends them to a target system.

(Is there a first dicom data actuator? I don't know. If there is one, this is another.)

The basic idea here: we'll run as a daemon and use watchdog to look for any files that show up in our target directory (or any subdirectories). Then, we'll make sure they're dicoms, and if they are, we'll read the study timestamp, exam number, and series number to unambiguously define what series the dicoms belong to. We'll spawn a thread (or process) and in that, we'll open a connecton to an FTP server, create a directory, and then upload all the dicoms to it. Afterwards, we'll open an SSH connection to the server and kick off a notification process. Woo!

yadda is going to provide the classes to make all this easy, with the expectation that end-users will actually write a little python script to make it actually go.
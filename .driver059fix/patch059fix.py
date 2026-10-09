from pathlib import Path

p = Path('driver/lib/screens/operations_job_screen.dart')
s = p.read_text()
old = 'MaterialPageRoute<void>(builder: (_) => ChatScreen(session: session, bookingId: job.id))'
new = 'MaterialPageRoute<void>(builder: (_) => DriverChatScreen(session: session, bookingId: job.id))'
if old not in s:
    raise SystemExit('operations chat class marker missing')
p.write_text(s.replace(old, new, 1))
print('Applied Driver v0.5.9 chat class hotfix.')

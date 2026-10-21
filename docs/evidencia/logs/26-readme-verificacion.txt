curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "  Revisar backups  ", "priority": 2, "due_date": "2030-12-31", "assignee_id": 1}'
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100   259  100   168  100    91  59511  32235 --:--:-- --:--:-- --:--:--  126k
HTTP/1.1 201 Created
date: Wed, 21 Oct 2026 17:09:14 GMT
server: uvicorn
content-length: 168
content-type: application/json

{"title":"Revisar backups","description":null,"priority":2,"due_date":"2030-12-31","assignee_id":1,"id":1,"status":"pending","created_at":"2026-10-21T17:09:14.550377Z"}echo

curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: alta-backup-001" \
  -d '{"title": "Rotar certificados", "assignee_id": 2}'
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100   212  100   163  100    49  51033  15341 --:--:-- --:--:-- --:--:-- 70666
HTTP/1.1 201 Created
date: Wed, 21 Oct 2026 17:09:14 GMT
server: uvicorn
content-length: 163
content-type: application/json

{"title":"Rotar certificados","description":null,"priority":3,"due_date":null,"assignee_id":2,"id":2,"status":"pending","created_at":"2026-10-21T17:09:14.557400Z"}echo

curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: alta-backup-001" \
  -d '{"title": "Rotar certificados", "assignee_id": 2}'
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100   212  100   163  100    49  93678  28160 --:--:-- --:--:-- --:--:--  207k
HTTP/1.1 200 OK
date: Wed, 21 Oct 2026 17:09:14 GMT
server: uvicorn
content-length: 163
content-type: application/json

{"title":"Rotar certificados","description":null,"priority":3,"due_date":null,"assignee_id":2,"id":2,"status":"pending","created_at":"2026-10-21T17:09:14.557400Z"}echo

curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: alta-backup-001" \
  -d '{"title": "Otra tarea distinta"}'
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100    93  100    61  100    32  31508  16528 --:--:-- --:--:-- --:--:-- 93000
HTTP/1.1 409 Conflict
date: Wed, 21 Oct 2026 17:09:14 GMT
server: uvicorn
content-length: 61
content-type: application/json

{"detail":"clave de idempotencia ya existe: alta-backup-001"}echo

curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "ab"}'
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100   163  100   148  100    15  82085   8319 --:--:-- --:--:-- --:--:--  159k
HTTP/1.1 422 Unprocessable Entity
date: Wed, 21 Oct 2026 17:09:14 GMT
server: uvicorn
content-length: 148
content-type: application/json

{"detail":[{"type":"string_too_short","loc":["body","title"],"msg":"String should have at least 3 characters","input":"ab","ctx":{"min_length":3}}]}echo

curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Tarea atrasada", "due_date": "2020-01-01"}'
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100   116  100    63  100    53  31374  26394 --:--:-- --:--:-- --:--:--  113k
HTTP/1.1 422 Unprocessable Entity
date: Wed, 21 Oct 2026 17:09:14 GMT
server: uvicorn
content-length: 63
content-type: application/json

{"detail":"la fecha límite no puede ser anterior a hoy (UTC)"}echo

curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Tarea huérfana", "assignee_id": 999}'
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100    87  100    39  100    48  22608  27826 --:--:-- --:--:-- --:--:-- 87000
HTTP/1.1 404 Not Found
date: Wed, 21 Oct 2026 17:09:14 GMT
server: uvicorn
content-length: 39
content-type: application/json

{"detail":"usuario no encontrado: 999"}echo

curl -i http://127.0.0.1:8000/tasks
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100   334  100   334    0     0   159k      0 --:--:-- --:--:-- --:--:--  163k
HTTP/1.1 200 OK
date: Wed, 21 Oct 2026 17:09:14 GMT
server: uvicorn
content-length: 334
content-type: application/json

[{"title":"Revisar backups","description":null,"priority":2,"due_date":"2030-12-31","assignee_id":1,"id":1,"status":"pending","created_at":"2026-10-21T17:09:14.550377Z"},{"title":"Rotar certificados","description":null,"priority":3,"due_date":null,"assignee_id":2,"id":2,"status":"pending","created_at":"2026-10-21T17:09:14.557400Z"}]echo

curl -i "http://127.0.0.1:8000/tasks?assignee_id=1"
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100   170  100   170    0     0  83702      0 --:--:-- --:--:-- --:--:-- 85000
HTTP/1.1 200 OK
date: Wed, 21 Oct 2026 17:09:14 GMT
server: uvicorn
content-length: 170
content-type: application/json

[{"title":"Revisar backups","description":null,"priority":2,"due_date":"2030-12-31","assignee_id":1,"id":1,"status":"pending","created_at":"2026-10-21T17:09:14.550377Z"}]echo

curl -i http://127.0.0.1:8000/tasks/1
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100   168  100   168    0     0  98418      0 --:--:-- --:--:-- --:--:--  164k
HTTP/1.1 200 OK
date: Wed, 21 Oct 2026 17:09:14 GMT
server: uvicorn
content-length: 168
content-type: application/json

{"title":"Revisar backups","description":null,"priority":2,"due_date":"2030-12-31","assignee_id":1,"id":1,"status":"pending","created_at":"2026-10-21T17:09:14.550377Z"}echo


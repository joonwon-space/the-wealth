#!/bin/sh
# Docker 내부 네트워크에서 비밀번호 없이 접속 가능하도록 pg_hba.conf 설정.
# postgres 컨테이너가 새로 생성될 때 자동 실행됨 (docker-entrypoint-initdb.d).
# 이미 설정된 경우 중복 추가 방지.

HBA=/var/lib/postgresql/data/pg_hba.conf

if grep -q "172.18.0.0/16" "$HBA"; then
    echo "pg_hba.conf: Docker network trust rule already present, skipping."
    exit 0
fi

# 마지막 host 라인(scram-sha-256 또는 0.0.0.0/0) 앞에 Docker 내부 네트워크 trust 규칙 삽입
if grep -q "scram-sha-256" "$HBA"; then
    sed -i '/^host all all all scram-sha-256/i host all all 172.18.0.0/16 trust' "$HBA"
else
    # fallback: 파일 끝에 추가
    echo "host all all 172.18.0.0/16 trust" >> "$HBA"
fi

echo "pg_hba.conf: Docker network trust rule added."

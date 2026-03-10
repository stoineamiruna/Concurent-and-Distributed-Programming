#!/usr/bin/env bash

mkdir -p results
LOG="results/log_$(date +%Y%m%d_%H%M%S).txt"
echo "start teste: $(date)" > "$LOG"

BLOCKS=(500 1000 5000 10000 32000 65535)
SIZES=(500 1000)

run_test() {
    local PROTO=$1
    local METHOD=$2
    local SIZE=$3
    local BLOCK=$4
    local SRV=$5
    local CLI=$6
    local PORT=$7

    echo ""
    echo "--- $PROTO | $METHOD | ${SIZE}MB | block=${BLOCK}B ---"
    echo "--- $PROTO | $METHOD | ${SIZE}MB | block=${BLOCK}B ---" >> "$LOG"

    # curata portul inainte de QUIC (UDP nu elibereaza portul instant)
    if [ "$PROTO" = "QUIC" ]; then
        pkill -f "$SRV" 2>/dev/null
        sleep 2
    fi

    python3 "$SRV" --port "$PORT" --method "$METHOD" &
    SRV_PID=$!
    sleep 1

    python3 "$CLI" --port "$PORT" --size "$SIZE" --block-size "$BLOCK" --method "$METHOD" 2>&1 | tee -a "$LOG"

    sleep 2
    kill "$SRV_PID" 2>/dev/null
    wait "$SRV_PID" 2>/dev/null

    # pentru QUIC asteapta mai mult sa se elibereze portul UDP
    if [ "$PROTO" = "QUIC" ]; then
        sleep 3
    else
        sleep 0.5
    fi
}

echo "TCP" >> "$LOG"
for SIZE in "${SIZES[@]}"; do
    for BLOCK in "${BLOCKS[@]}"; do
        run_test "TCP" "streaming" "$SIZE" "$BLOCK" "tcp_server.py" "tcp_client.py" 5001
    done
done

for BLOCK in 1000 10000 65535; do
    run_test "TCP" "stop-and-wait" 500 "$BLOCK" "tcp_server.py" "tcp_client.py" 5001
done

echo "UDP" >> "$LOG"
for SIZE in "${SIZES[@]}"; do
    for BLOCK in "${BLOCKS[@]}"; do
        run_test "UDP" "streaming"     "$SIZE" "$BLOCK" "udp_server.py" "udp_client.py" 5002
        run_test "UDP" "stop-and-wait" "$SIZE" "$BLOCK" "udp_server.py" "udp_client.py" 5002
    done
done

echo "QUIC" >> "$LOG"
if [ ! -f cert.pem ] || [ ! -f key.pem ]; then
    echo "lipsesc cert.pem / key.pem, ruleaza gen_certs.sh"
else
    for SIZE in "${SIZES[@]}"; do
        for BLOCK in "${BLOCKS[@]}"; do
            run_test "QUIC" "streaming"     "$SIZE" "$BLOCK" "quic_server.py" "quic_client.py" 5003
            run_test "QUIC" "stop-and-wait" "$SIZE" "$BLOCK" "quic_server.py" "quic_client.py" 5003
        done
    done
fi

echo ""
echo "gata, rezultate in $LOG"
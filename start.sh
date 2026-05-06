#!/bin/bash
cd ~/Desktop/oraculo-era-acuario

echo ""
echo "⬡  Iniciando el Oráculo Digital Era de Acuario..."
echo ""

if [ ! -d "venv" ]; then
    echo "→ Creando entorno virtual..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "→ Instalando dependencias..."
pip install -r requirements.txt -q

echo ""
echo "✓ Todo listo. Abriendo el Oráculo..."
echo ""
echo "  → API:  http://localhost:8000"
echo "  → Docs: http://localhost:8000/docs"
echo ""

sleep 1 && open http://localhost:8000/docs &

venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

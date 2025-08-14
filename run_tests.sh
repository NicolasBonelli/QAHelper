#!/bin/bash

# Script para ejecutar tests de QAHelper
# Uso: ./run_tests.sh [opciones]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para mostrar ayuda
show_help() {
    echo "Uso: $0 [opciones]"
    echo ""
    echo "Opciones:"
    echo "  -h, --help              Mostrar esta ayuda"
    echo "  -u, --unit              Ejecutar solo tests unitarios"
    echo "  -i, --integration       Ejecutar solo tests de integración"
    echo "  -s, --supervisor        Ejecutar solo tests del supervisor"
    echo "  -p, --performance       Ejecutar tests de performance"
    echo "  -a, --all               Ejecutar todos los tests (default)"
    echo "  -c, --coverage          Generar reporte de cobertura"
    echo "  -v, --verbose           Modo verbose"
    echo "  -f, --fast              Ejecutar tests rápidos (sin tests lentos)"
    echo "  --clean                 Limpiar archivos de cache antes de ejecutar"
    echo ""
    echo "Ejemplos:"
    echo "  $0                      # Ejecutar todos los tests"
    echo "  $0 -u                   # Solo tests unitarios"
    echo "  $0 -i -c                # Tests de integración con cobertura"
    echo "  $0 -s -v                # Tests del supervisor en modo verbose"
}

# Variables por defecto
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_SUPERVISOR=false
RUN_PERFORMANCE=false
RUN_ALL=true
GENERATE_COVERAGE=false
VERBOSE=false
FAST_MODE=false
CLEAN_CACHE=false

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--unit)
            RUN_UNIT=true
            RUN_ALL=false
            shift
            ;;
        -i|--integration)
            RUN_INTEGRATION=true
            RUN_ALL=false
            shift
            ;;
        -s|--supervisor)
            RUN_SUPERVISOR=true
            RUN_ALL=false
            shift
            ;;
        -p|--performance)
            RUN_PERFORMANCE=true
            RUN_ALL=false
            shift
            ;;
        -a|--all)
            RUN_ALL=true
            shift
            ;;
        -c|--coverage)
            GENERATE_COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--fast)
            FAST_MODE=true
            shift
            ;;
        --clean)
            CLEAN_CACHE=true
            shift
            ;;
        *)
            print_error "Opción desconocida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Función para limpiar cache
clean_cache() {
    print_message "Limpiando archivos de cache..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    find . -name "coverage.xml" -delete 2>/dev/null || true
    rm -rf htmlcov/ 2>/dev/null || true
    print_success "Cache limpiado"
}

# Función para verificar dependencias
check_dependencies() {
    print_message "Verificando dependencias..."
    
    # Verificar Python
    if ! command -v python &> /dev/null; then
        print_error "Python no está instalado"
        exit 1
    fi
    
    # Verificar pip
    if ! command -v pip &> /dev/null; then
        print_error "pip no está instalado"
        exit 1
    fi
    
    # Verificar pytest
    if ! python -c "import pytest" &> /dev/null; then
        print_warning "pytest no está instalado. Instalando..."
        pip install pytest pytest-cov pytest-asyncio
    fi
    
    print_success "Dependencias verificadas"
}

# Función para ejecutar tests
run_tests() {
    local test_type=$1
    local test_path=$2
    local test_name=$3
    
    print_message "Ejecutando $test_name..."
    
    local pytest_args=""
    
    if [ "$VERBOSE" = true ]; then
        pytest_args="$pytest_args -v"
    fi
    
    if [ "$GENERATE_COVERAGE" = true ]; then
        pytest_args="$pytest_args --cov=backend --cov-report=html:htmlcov --cov-report=xml:coverage.xml --cov-report=term-missing"
    fi
    
    if [ "$FAST_MODE" = true ]; then
        pytest_args="$pytest_args -m 'not slow'"
    fi
    
    # Ejecutar tests
    if python -m pytest $test_path $pytest_args; then
        print_success "$test_name completados exitosamente"
    else
        print_error "$test_name fallaron"
        return 1
    fi
}

# Función principal
main() {
    print_message "Iniciando ejecución de tests de QAHelper..."
    
    # Limpiar cache si se solicita
    if [ "$CLEAN_CACHE" = true ]; then
        clean_cache
    fi
    
    # Verificar dependencias
    check_dependencies
    
    # Contador de tests ejecutados
    tests_run=0
    tests_failed=0
    
    # Ejecutar tests según las opciones
    if [ "$RUN_ALL" = true ] || [ "$RUN_UNIT" = true ]; then
        if run_tests "unit" "tests/test_unit.py" "Tests unitarios"; then
            ((tests_run++))
        else
            ((tests_failed++))
        fi
    fi
    
    if [ "$RUN_ALL" = true ] || [ "$RUN_INTEGRATION" = true ]; then
        if run_tests "integration" "tests/test_integration.py" "Tests de integración"; then
            ((tests_run++))
        else
            ((tests_failed++))
        fi
    fi
    
    if [ "$RUN_ALL" = true ] || [ "$RUN_SUPERVISOR" = true ]; then
        if run_tests "supervisor" "tests/test_supervisor_architecture.py" "Tests del supervisor"; then
            ((tests_run++))
        else
            ((tests_failed++))
        fi
    fi
    
    if [ "$RUN_PERFORMANCE" = true ]; then
        if run_tests "performance" "tests/test_integration.py::TestPerformanceIntegration" "Tests de performance"; then
            ((tests_run++))
        else
            ((tests_failed++))
        fi
    fi
    
    # Resumen final
    echo ""
    print_message "Resumen de ejecución:"
    echo "  Tests ejecutados: $tests_run"
    echo "  Tests fallidos: $tests_failed"
    
    if [ "$tests_failed" -eq 0 ]; then
        print_success "¡Todos los tests pasaron exitosamente!"
        
        if [ "$GENERATE_COVERAGE" = true ]; then
            print_message "Reporte de cobertura generado en htmlcov/index.html"
        fi
        
        exit 0
    else
        print_error "Algunos tests fallaron"
        exit 1
    fi
}

# Ejecutar función principal
main "$@"
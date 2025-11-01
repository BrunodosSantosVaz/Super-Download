#!/bin/bash

# Script de empacotamento do Super-Download Flatpak
# Autor: Bruno Vaz
# Descrição: Automatiza o processo de build, versionamento e distribuição do Flatpak

set -e  # Sai em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
APP_ID="br.com.superdownload"
MANIFEST="flatpak/com.superdownload.yml"
BUILD_DIR="build-dir"
REPO_DIR="flatpak-repo"
BUNDLE_NAME="super-download"

# Funções auxiliares
print_header() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Obter versão atual do pyproject.toml
get_current_version() {
    grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'
}

# Atualizar versão no pyproject.toml
update_version() {
    local new_version=$1
    sed -i "s/^version = .*/version = \"$new_version\"/" pyproject.toml
    print_success "Versão atualizada para $new_version em pyproject.toml"
}

# Incrementar versão automaticamente
increment_version() {
    local version=$1
    local type=$2

    IFS='.' read -r major minor patch <<< "$version"

    case $type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            print_error "Tipo de versão inválido: $type"
            exit 1
            ;;
    esac

    echo "$major.$minor.$patch"
}

# Verificar dependências
check_dependencies() {
    print_header "Verificando Dependências"

    local deps=("flatpak-builder" "flatpak" "convert")
    local missing=()

    for dep in "${deps[@]}"; do
        if command -v "$dep" &> /dev/null; then
            print_success "$dep instalado"
        else
            print_error "$dep não encontrado"
            missing+=("$dep")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        print_error "Dependências faltando: ${missing[*]}"
        print_info "Instale com: sudo pacman -S flatpak-builder flatpak imagemagick"
        exit 1
    fi
}

# Limpar builds anteriores
clean_build() {
    print_header "Limpando Builds Anteriores"

    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
        print_success "Diretório $BUILD_DIR removido"
    fi

    if [ -d ".flatpak-builder" ]; then
        rm -rf ".flatpak-builder"
        print_success "Cache .flatpak-builder removido"
    fi
}

# Construir o Flatpak
build_flatpak() {
    print_header "Construindo Flatpak"

    # Renomear setup.py temporariamente para evitar conflitos
    if [ -f "setup.py" ]; then
        mv setup.py setup.py.bak
        print_info "setup.py temporariamente renomeado"
    fi

    # Build
    print_info "Iniciando build..."
    if flatpak-builder --force-clean "$BUILD_DIR" "$MANIFEST"; then
        print_success "Build concluído com sucesso"
    else
        print_error "Falha no build"
        # Restaurar setup.py
        [ -f "setup.py.bak" ] && mv setup.py.bak setup.py
        exit 1
    fi

    # Restaurar setup.py
    if [ -f "setup.py.bak" ]; then
        mv setup.py.bak setup.py
        print_info "setup.py restaurado"
    fi
}

# Instalar localmente
install_local() {
    print_header "Instalando Localmente"

    # Desinstalar versão anterior se existir
    if flatpak list --app | grep -q "$APP_ID"; then
        print_info "Desinstalando versão anterior..."
        flatpak uninstall -y "$APP_ID" 2>/dev/null || true
    fi

    # Instalar
    print_info "Instalando nova versão..."
    if flatpak-builder --user --install --force-clean "$BUILD_DIR" "$MANIFEST"; then
        print_success "Instalação local concluída"
    else
        print_error "Falha na instalação"
        exit 1
    fi
}

# Selecionar branch interativamente
select_branch() {
    echo ""
    print_info "Selecione o branch:"
    echo "  1) stable   (produção)"
    echo "  2) beta     (testes públicos)"
    echo "  3) dev      (desenvolvimento)"
    echo ""
    read -p "Escolha (1-3) [1]: " choice
    choice=${choice:-1}

    case $choice in
        1) echo "stable" ;;
        2) echo "beta" ;;
        3) echo "dev" ;;
        *) echo "stable" ;;
    esac
}

# Selecionar ou atualizar versão
select_version() {
    local current_version=$(get_current_version)
    echo ""
    print_info "Versão atual: $current_version"
    read -p "Nova versão (Enter para manter): " new_version

    if [ -z "$new_version" ]; then
        echo "$current_version"
    else
        echo "$new_version"
    fi
}

# Criar repositório Flatpak
create_repo() {
    print_header "Criando Repositório Flatpak"

    local version=$1
    local branch=${2:-stable}

    # Criar diretório do repositório se não existir
    if [ ! -d "$REPO_DIR" ]; then
        mkdir -p "$REPO_DIR"
        ostree init --repo="$REPO_DIR" --mode=archive-z2
        print_success "Repositório criado em $REPO_DIR"
    fi

    # Exportar para o repositório com branch específico
    print_info "Exportando para repositório (branch: $branch)..."
    flatpak-builder --repo="$REPO_DIR" --force-clean --default-branch="$branch" "$BUILD_DIR" "$MANIFEST"
    print_success "Exportação concluída"
}

# Criar bundle (.flatpak)
create_bundle() {
    print_header "Criando Bundle Flatpak"

    local version=$1
    local branch=${2:-stable}
    local bundle_file="${BUNDLE_NAME}-${version}-${branch}.flatpak"

    # Criar bundle com branch específico
    print_info "Criando bundle $bundle_file (branch: $branch)..."
    if flatpak build-bundle "$REPO_DIR" "$bundle_file" "$APP_ID" "$branch"; then
        print_success "Bundle criado: $bundle_file"
        print_info "Tamanho: $(du -h "$bundle_file" | cut -f1)"
    else
        print_error "Falha ao criar bundle"
        exit 1
    fi
}

# Testar instalação
test_installation() {
    print_header "Testando Instalação"

    print_info "Verificando aplicativo instalado..."
    if flatpak list --app | grep -q "$APP_ID"; then
        print_success "Aplicativo encontrado"

        print_info "Informações do aplicativo:"
        flatpak info "$APP_ID" | grep -E "(ID|Ref|Instalado)"

        print_success "Instalação OK"
    else
        print_error "Aplicativo não encontrado"
        exit 1
    fi
}

# Menu de ajuda
show_help() {
    cat << EOF
Uso: $0 [OPÇÃO] [ARGUMENTOS]

Opções:
  build                 Apenas construir o Flatpak (não instala)
  install              Construir e instalar localmente
  bundle               Criar bundle .flatpak (pergunta versão e branch)
  release [TYPE]       Criar release completo (major|minor|patch)
  clean                Limpar builds anteriores
  version [NEW]        Atualizar versão manualmente
  test                 Testar aplicativo instalado
  help                 Mostrar esta ajuda

Branches disponíveis:
  stable               Versão de produção estável
  beta                 Versão de testes públicos
  dev                  Versão de desenvolvimento

Exemplos:
  $0 install                  # Build e instala localmente
  $0 bundle                   # Cria bundle (interativo: pergunta versão e branch)
  $0 release patch           # Incrementa patch e cria release
  $0 release minor           # Incrementa minor e cria release
  $0 version 1.0.0           # Atualiza versão para 1.0.0

EOF
}

# Comando principal
main() {
    local command=${1:-help}

    case $command in
        build)
            check_dependencies
            clean_build
            build_flatpak
            print_success "Build concluído!"
            ;;

        install)
            check_dependencies
            clean_build
            build_flatpak
            install_local
            test_installation
            print_success "Instalação concluída!"
            ;;

        bundle)
            local version=$(select_version)
            local branch=$(select_branch)

            # Atualizar versão se mudou
            local current=$(get_current_version)
            if [ "$version" != "$current" ]; then
                update_version "$version"
            fi

            check_dependencies
            clean_build
            build_flatpak
            create_repo "$version" "$branch"
            create_bundle "$version" "$branch"
            print_success "Bundle criado com sucesso!"
            print_info "Bundle: ${BUNDLE_NAME}-${version}-${branch}.flatpak"
            ;;

        release)
            local type=${2:-patch}
            local current_version=$(get_current_version)
            local new_version=$(increment_version "$current_version" "$type")
            local branch=$(select_branch)

            print_header "Criando Release $new_version"
            print_info "Versão atual: $current_version"
            print_info "Nova versão: $new_version"
            print_info "Branch: $branch"

            # Atualizar versão
            update_version "$new_version"

            # Build completo
            check_dependencies
            clean_build
            build_flatpak
            install_local
            create_repo "$new_version" "$branch"
            create_bundle "$new_version" "$branch"
            test_installation

            print_success "Release $new_version criado com sucesso!"
            print_info "Bundle: ${BUNDLE_NAME}-${new_version}-${branch}.flatpak"
            ;;

        clean)
            clean_build
            print_success "Limpeza concluída!"
            ;;

        version)
            local new_version=$2
            if [ -z "$new_version" ]; then
                print_info "Versão atual: $(get_current_version)"
            else
                update_version "$new_version"
            fi
            ;;

        test)
            test_installation
            ;;

        help|--help|-h)
            show_help
            ;;

        *)
            print_error "Comando desconhecido: $command"
            show_help
            exit 1
            ;;
    esac
}

# Executar script
main "$@"

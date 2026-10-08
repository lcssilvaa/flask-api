from flask import Flask
from flask import request
from flask import render_template
from flask import jsonify, redirect, url_for
from contextlib import closing
from datetime import date
from math import isfinite
from pathlib import Path
import sqlite3
from sqlite3 import Error

#######################################################
# Instância da Aplicação Flask

app = Flask(__name__)

DB_PATH = Path(__file__).resolve().parent / 'db-produtos.db'


def conectar_banco():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                idproduto INTEGER PRIMARY KEY,
                descricao TEXT NOT NULL,
                precocompra REAL NOT NULL,
                precovenda REAL NOT NULL,
                datacriacao TEXT NOT NULL
            )
        ''')
        conn.commit()
    except Error:
        conn.close()
        raise
    return conn


def coluna_id(conn):
    # Bancos antigos usam "id"; bancos novos usam "idproduto".
    colunas = {coluna['name'] for coluna in conn.execute('PRAGMA table_info(produtos)')}
    if 'idproduto' in colunas:
        return 'idproduto'
    if 'id' in colunas:
        return 'id'
    raise Error('A tabela produtos não possui uma coluna de identificação.')


def resposta_json():
    return (request.is_json or request.method in ('PUT', 'DELETE')
            or request.accept_mimetypes.best == 'application/json')


def erro(mensagem, status):
    if resposta_json():
        return jsonify(mensagem=mensagem), status
    return mensagem, status, {'Content-Type': 'text/plain; charset=utf-8'}


def ler_produto():
    if request.is_json:
        dados = request.get_json(silent=True)
        if not isinstance(dados, dict):
            raise ValueError('Envie um objeto JSON válido.')
    else:
        dados = request.form

    descricao = dados.get('descricao')
    if not isinstance(descricao, str) or not descricao.strip():
        raise ValueError('Informe a descrição do produto.')

    precos = []
    for campo in ('precocompra', 'precovenda'):
        valor = dados.get(campo)
        if isinstance(valor, bool):
            raise ValueError(f'Informe um número válido em {campo}.')
        try:
            valor = float(valor)
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f'Informe um número válido em {campo}.') from None
        if not isfinite(valor) or valor < 0:
            raise ValueError(f'{campo} deve ser um número finito maior ou igual a zero.')
        precos.append(valor)

    return descricao.strip(), precos[0], precos[1]

#######################################################
# 1. Cadastrar produtos

@app.route('/produtos/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'GET':
        return render_template('cadastrar.html', mensagem='')

    try:
        registro = ler_produto()
    except ValueError as e:
        if resposta_json():
            return erro(str(e), 400)
        return render_template('cadastrar.html', mensagem=str(e)), 400

    with closing(conectar_banco()) as conn:
        with conn:
            cur = conn.execute('''
                INSERT INTO produtos (descricao, precocompra, precovenda, datacriacao)
                VALUES (?, ?, ?, ?)
            ''', (*registro, date.today().isoformat()))
        idproduto = cur.lastrowid

    if resposta_json():
        return jsonify(mensagem='Sucesso - cadastrado', idproduto=idproduto), 201
    return render_template('cadastrar.html', mensagem='Sucesso - cadastrado')


#######################################################
# 2. Listar produtos

@app.route('/produtos/listar', methods=['GET'])
def listar():
    with closing(conectar_banco()) as conn:
        identificador = coluna_id(conn)
        registros = conn.execute(f'''
            SELECT {identificador} AS idproduto, descricao,
                   precocompra, precovenda, datacriacao
            FROM produtos ORDER BY {identificador}
        ''').fetchall()

    if resposta_json():
        return jsonify([dict(registro) for registro in registros])
    return render_template('listar.html', regs=registros)


#######################################################
# Rota de Erro

@app.errorhandler(404)
def pagina_nao_encontrada(e):
    if resposta_json():
        return erro('Página não encontrada.', 404)
    return render_template('error.html'), 404


@app.errorhandler(Error)
def erro_banco(e):
    app.logger.exception('Erro ao acessar o banco de produtos')
    return erro('Erro ao acessar o banco de produtos.', 500)

#######################################################
# Rota de Excluir

@app.route('/produtos/excluir/<int:idproduto>', methods=['POST', 'DELETE'])
def excluir(idproduto):
    with closing(conectar_banco()) as conn:
        identificador = coluna_id(conn)
        with conn:
            cur = conn.execute(
                f'DELETE FROM produtos WHERE {identificador} = ?', (idproduto,)
            )
        if cur.rowcount == 0:
            return erro('Produto não encontrado.', 404)

    if resposta_json():
        return jsonify(mensagem='Sucesso - excluído', idproduto=idproduto)
    return redirect(url_for('listar'))


#######################################################
# Rota de Editar

@app.route('/produtos/editar/<int:idproduto>', methods=['GET', 'POST', 'PUT'])
def editar(idproduto):
    with closing(conectar_banco()) as conn:
        identificador = coluna_id(conn)
        produto = conn.execute(f'''
            SELECT {identificador} AS idproduto, descricao,
                   precocompra, precovenda, datacriacao
            FROM produtos WHERE {identificador} = ?
        ''', (idproduto,)).fetchone()

        if produto is None:
            return erro('Produto não encontrado.', 404)

        if request.method == 'GET':
            if resposta_json():
                return jsonify(dict(produto))
            return render_template('editar.html', produto=produto)

        try:
            registro = ler_produto()
        except ValueError as e:
            if resposta_json():
                return erro(str(e), 400)
            return render_template('editar.html', produto=produto, mensagem=str(e)), 400

        with conn:
            cur = conn.execute(f'''
                UPDATE produtos
                SET descricao = ?, precocompra = ?, precovenda = ?
                WHERE {identificador} = ?
            ''', (*registro, idproduto))
        if cur.rowcount == 0:
            return erro('Produto não encontrado.', 404)

    if resposta_json():
        return jsonify(mensagem='Sucesso - editado', idproduto=idproduto)
    return redirect(url_for('listar'))

#######################################################
# Execução da Aplicação

if __name__ == '__main__':
    app.run(port=5001, debug=True)

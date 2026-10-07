from flask import Flask
from flask import request
from flask import render_template
from datetime import date
from pathlib import Path
import sqlite3
from sqlite3 import Error

#######################################################
# Instância da Aplicação Flask

app = Flask(__name__)

DB_PATH = Path(__file__).resolve().parent / 'db-produtos.db'


def conectar_banco():
    conn = sqlite3.connect(DB_PATH)
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

#######################################################
# 1. Cadastrar produtos

@app.route('/produtos/cadastrar', methods=['GET', 'POST'])
def cadastrar():

    mensagem = ''

    if request.method == 'POST':
        descricao = request.form['descricao']
        precocompra = request.form['precocompra']
        precovenda = request.form['precovenda']
        datacriacao = date.today()

        mensagem = 'Erro - não cadastrado'

        if descricao and precocompra and precovenda:
            registro = (
                descricao,
                precocompra,
                precovenda,
                datacriacao
            )

            conn = None

            try:
                conn = conectar_banco()

                sql = '''
                    INSERT INTO produtos
                    (descricao, precocompra, precovenda, datacriacao)
                    VALUES (?, ?, ?, ?)
                '''

                cur = conn.cursor()
                cur.execute(sql, registro)
                conn.commit()

                mensagem = 'Sucesso - cadastrado'

            except Error as e:
                print(e)

            finally:
                if conn:
                    conn.close()

    return render_template(
        'cadastrar.html',
        mensagem=mensagem
    )


#######################################################
# 2. Listar produtos

@app.route('/produtos/listar', methods=['GET'])
def listar():

    conn = None

    try:
        conn = conectar_banco()

        sql = '''
            SELECT descricao, precocompra, precovenda, datacriacao FROM produtos
        '''

        cur = conn.cursor()
        cur.execute(sql)

        registros = cur.fetchall()

        return render_template(
            'listar.html',
            regs=registros
        )

    except Error as e:
        print(e)
        return 'Erro ao consultar produtos'

    finally:
        if conn:
            conn.close()


#######################################################
# Rota de Erro

@app.errorhandler(404)
def pagina_nao_encontrada(e):
    return render_template('error.html'), 404

#######################################################
# Rota de Excluir

@app.route('/produtos/excluir/<int:idproduto>', methods=['POST'])
def excluir(idproduto):
    return f'Produto recebido para exclusão: {idproduto}'

#######################################################
# Execução da Aplicação

if __name__ == '__main__':
    app.run(port=5501, debug=True)

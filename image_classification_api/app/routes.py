from . import app, db, sync_job_counters, start_time
from flask import request, jsonify
from .utils import allowed_file, generate_unique_id, classify_image, process_image_async
from werkzeug.utils import secure_filename
import os
import threading
import time
import logging
logging.basicConfig(level=logging.INFO)


@app.route('/upload_image', methods=['POST'])
def upload_image():
    # have another

    if 'image' not in request.files:
        sync_job_counters.update_one({'_id': 'counters'}, {'$inc': {'error_count': 1}})
        return jsonify({'error': {'code': 400, 'message': 'No file part'}}), 400

    file = request.files['image']

    if file.filename == '':
        sync_job_counters.update_one({'_id': 'counters'}, {'$inc': {'error_count': 1}})
        return jsonify({'error': {'code': 400, 'message': 'No selected file'}}), 400

    if file and allowed_file(file.filename):
        try:
            sync_job_counters.update_one({'_id': 'counters'}, {'$inc': {'running_count': 1}})
            filename = secure_filename(file.filename)
            filepath = os.path.join('/tmp', filename)
            file.save(filepath)

            # Call the classification function
            matches = classify_image(filepath)

            sync_job_counters.update_one({'_id': 'counters'}, {'$inc': {'running_count': -1, 'success_count': 1}})
            return jsonify({'matches': matches}), 200
        except Exception:
            # Update counters: decrement running, increment error
            sync_job_counters.update_one({'_id': 'counters'}, {'$inc': {'running_count': -1, 'error_count': 1}})
            return jsonify({'error': {'code': 500, 'message': 'An error occurred during processing'}}), 500

    sync_job_counters.update_one({'_id': 'counters'}, {'$inc': {'error_count': 1}})
    return jsonify({'error': {'code': 400, 'message': 'File type not allowed'}}), 400


@app.route('/async_upload', methods=['POST'])
def async_upload():
    # log the request and which gunicorn worker is handling it:
    logging.info(f"Request received by worker {os.getpid()}")

    if 'image' not in request.files:
        return jsonify({'error': {'code': 400, 'message': 'No file part'}}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': {'code': 400, 'message': 'No selected file'}}), 400

    if file and allowed_file(file.filename):
        request_id = generate_unique_id()
        # make a variable filename that will be the request_id plus the extension of the file
        filename = str(request_id) + '.' + file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(filename)
        filepath = os.path.join('/tmp', filename)
        file.save(filepath)

        # Save the request status as 'running'
        db.requests.insert_one({
            'request_id': request_id,
            'status': 'running'
        })

        # Start background processing
        threading.Thread(target=process_image_async, args=(filepath, request_id)).start()

        # process = multiprocessing.Process(target=process_image_async, args=(filepath, request_id))
        # process.start()

        return jsonify({'request_id': request_id}), 202

    return jsonify({'error': {'code': 400, 'message': 'File type not allowed'}}), 400




@app.route('/result/<request_id>', methods=['GET'])
def get_result(request_id):
    try:
        request_id = int(request_id)
        request_data = db.requests.find_one({'request_id': request_id})
    except ValueError:
        return jsonify({'error': {'code': 404, 'message': 'ID not found'}}), 404

    if not request_data:
        return jsonify({'error': {'code': 404, 'message': 'ID not found'}}), 404

    if request_data['status'] == 'running':
        return jsonify({'status': 'running'}), 200

    if request_data['status'] == 'completed':
        return jsonify({
            'status': 'completed',
            'matches': request_data['matches']
        }), 200

    if request_data['status'] == 'error':
        return jsonify({
            'status': 'error',
            'error': request_data['error']
        }), 500

    print('This should not happen' + 'n' * 100)


@app.route('/status', methods=['GET'])
def get_status():
    processed = {
        # async + sync
        'success': db.requests.count_documents({'status': 'completed'}) + db.counters.find_one(
            {'_id': 'counters'})['success_count'],
        'fail': db.requests.count_documents({'status': 'error'}) + db.counters.find_one(
            {'_id': 'counters'})['error_count'],
        'running': db.requests.count_documents({'status': 'running'}) + db.counters.find_one(
            {'_id': 'counters'})['running_count'],
        'queued': 0  # we did not implement a queue
    }

    return jsonify({
        'status': {
            'uptime': time.time() - start_time,
            'processed': processed,
            'health': 'ok',
            'api_version': 2
        }
    }), 200
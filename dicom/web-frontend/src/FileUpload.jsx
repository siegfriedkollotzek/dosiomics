import {useCallback, useState} from 'react';
import {useDropzone} from 'react-dropzone';
import PropTypes from "prop-types";
import {urls} from "./common.js";
import Cookies from "js-cookie";

export const FileUpload = ({setFileData}) => {
  const [uploadStatus, setUploadStatus] = useState(null);
  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    const formData = new FormData();
    formData.append('file', file);
    setUploadStatus('Uploading...');
    fetch(urls.upload, {
      method: 'post',
      headers: {'X-CSRFToken': Cookies.get('csrftoken') || ""},
      body: formData
    })
      .then(response => response.json())
      .then(response => {
        setUploadStatus('Upload successful');
        if ('error' in response)
          alert(response.error)
        else if ('beams' in response) {
          setFileData(response)
        } else alert('unknown error')
      })
      .catch(error => {
        setUploadStatus('Upload failed');
        console.error('Error uploading file:', error);
      });
  }, []);
  const {getRootProps, getInputProps, isDragActive} = useDropzone({onDrop});
  return (
    <div {...getRootProps()} style={styles.dropzone}>
      <input {...getInputProps()} />
      {isDragActive ?
        <p>Drop the files here...</p> :
        <p>Drag &apos;n drop some files here, or click to select files</p>
      }
      {uploadStatus && <p>{uploadStatus}</p>}
    </div>
  );
};
const styles = {
  dropzone: {
    border: '2px dashed #cccccc',
    borderRadius: '4px',
    padding: '20px',
    textAlign: 'center',
    cursor: 'pointer'
  }
};

FileUpload.propTypes = {
  setFileData: PropTypes.func,
}

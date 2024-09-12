import {useEffect, useState} from 'react'
import './App.scss'
import {FileUpload} from './FileUpload';
import {Button, ButtonGroup, Col, Container, Form, Image, Row} from 'react-bootstrap';
import {FaAngleLeft, FaAngleRight} from 'react-icons/fa';
import {urls} from "./common.js";


export const App = () => {
  const [beamSelected, setBeamSelected] = useState('');
  const [controlPointSelected, setControlPointSelected] = useState('');
  const [fileData, setFileData] = useState(null);

  const beam = () => fileData && fileData.beams && fileData.beams.length > 0 && beamSelected && fileData.beams[Number(beamSelected)];

  useEffect(() => {
    if (fileData && fileData.beams.length > 0) {
      setBeamSelected('0')
      setControlPointSelected('0')
    } else {
      setBeamSelected('')
      setControlPointSelected('')
    }
  }, [fileData]);

  return (
    <>
      <Container className={"pt-4 pb-5"}>
        <Row className="mb-3">
          <Col lg={5} md={12} className={"pt-5"}>

            <FileUpload setFileData={setFileData}/>

            {fileData && fileData.beams && <>
              <p className={"mt-3 mb-3"}>File ID: {fileData ? fileData.uuid : "Nothing loaded."}</p>
              <Form>
                <Form.Group className={'mb-4 mt-4'}>
                  <Form.Label>Select Beam Sequence</Form.Label>
                  <Form.Select
                    value={beamSelected}
                    onChange={(e) => setBeamSelected(e.target.value)}
                  >
                    <option value="">Select Beam</option>
                    {fileData.beams.map(beam => (
                      <option key={beam.index} value={beam.index}>
                        {beam.name}
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>

                {beamSelected && beam() &&
                  <Form.Group className={'mb-4 mt-4'}>
                    <Form.Label className={"me-2"}>Select Beam Sequence:</Form.Label>
                    <ButtonGroup>
                      <Button variant="secondary"
                              onClick={() => setControlPointSelected((Number(controlPointSelected) - 1).toString())}
                              disabled={Number(controlPointSelected) === Math.min(...beam().control_points)}>
                        <FaAngleLeft/>
                      </Button>
                      <Button variant="secondary" disabled>{controlPointSelected}</Button>
                      <Button variant="secondary"
                              onClick={() => setControlPointSelected((Number(controlPointSelected) + 1).toString())}
                              disabled={Number(controlPointSelected) === Math.max(...beam().control_points)}>
                        <FaAngleRight/>
                      </Button>
                    </ButtonGroup>
                  </Form.Group>
                }
              </Form>
            </>}
          </Col>

          <Col lg={7} md={12} className="text-center">
            <div>
              {beamSelected && fileData && fileData.beams &&
                <Image src={urls.plotControlPoints + `${fileData.uuid}/${beamSelected}/${controlPointSelected}/`}
                       rounded style={{maxWidth: "95%"}}/>
              }
            </div>
          </Col>
        </Row>
      </Container>
    </>
  )
}

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import node from '../Node';
import gamepads from '../Gamepads';

const GamepadView = () => {
  const { index } = useParams();
  const [gamepad, setGamepad] = useState(null);
  
  useEffect(() => {
    // Set initial gamepad if available
    if (gamepads.gamepads[index]) {
      setGamepad(gamepads.gamepads[index]);
    }
    
    // Listen for gamepad connection
    const handleGamepadConnected = (connectedGamepad) => {
      if (connectedGamepad.index === parseInt(index)) {
        setGamepad(connectedGamepad);
      }
    };
    
    gamepads.on('gamepadconnected', handleGamepadConnected);
    
    // Poll for gamepad updates
    const pollInterval = setInterval(() => {
      if (gamepads.gamepads[index]) {
        setGamepad({...gamepads.gamepads[index]});
      }
    }, 100);
    
    return () => {
      clearInterval(pollInterval);
    };
  }, [index]);
  
  if (!gamepad) {
    return (
      <div className="controller" style={{ margin: '20px' }}>
        <h3>Gamepad {index} Not Connected</h3>
        <p>Please connect a gamepad and make sure it's recognized by the browser.</p>
      </div>
    );
  }
  
  return (
    <div className="controller" style={{ margin: '20px' }}>
      <h6>{gamepad.id}</h6>
      <div className="grid">
        <div className="s4">
          <table className="stripes">
            <tbody>
              <tr>
                <th>LEFT_ANALOG_STICK X</th>
                <td>{gamepad.LEFT_ANALOG_STICK_X?.value}</td>
              </tr>
              <tr>
                <th>LEFT_ANALOG_STICK Y</th>
                <td>{gamepad.LEFT_ANALOG_STICK_Y?.value}</td>
              </tr>
              <tr>
                <th>RIGHT_ANALOG_STICK X</th>
                <td>{gamepad.RIGHT_ANALOG_STICK_X?.value}</td>
              </tr>
              <tr>
                <th>RIGHT_ANALOG_STICK Y</th>
                <td>{gamepad.RIGHT_ANALOG_STICK_Y?.value}</td>
              </tr>
              <tr>
                <th>DPAD_UP</th>
                <td>{gamepad.DPAD_UP?.value}</td>
              </tr>
              <tr>
                <th>DPAD_DOWN</th>
                <td>{gamepad.DPAD_DOWN?.value}</td>
              </tr>
              <tr>
                <th>DPAD_LEFT</th>
                <td>{gamepad.DPAD_LEFT?.value}</td>
              </tr>
              <tr>
                <th>DPAD_RIGHT</th>
                <td>{gamepad.DPAD_RIGHT?.value}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="s4">
          <table className="stripes">
            <tbody>
              <tr>
                <th>FACE_1</th>
                <td>{gamepad.FACE_1?.value}</td>
              </tr>
              <tr>
                <th>FACE_2</th>
                <td>{gamepad.FACE_2?.value}</td>
              </tr>
              <tr>
                <th>FACE_3</th>
                <td>{gamepad.FACE_3?.value}</td>
              </tr>
              <tr>
                <th>FACE_4</th>
                <td>{gamepad.FACE_4?.value}</td>
              </tr>
              <tr>
                <th>LEFT_SHOULDER</th>
                <td>{gamepad.LEFT_SHOULDER?.value}</td>
              </tr>
              <tr>
                <th>RIGHT_SHOULDER</th>
                <td>{gamepad.RIGHT_SHOULDER?.value}</td>
              </tr>
              <tr>
                <th>LEFT_SHOULDER_BOTTOM</th>
                <td>{gamepad.LEFT_SHOULDER_BOTTOM?.value}</td>
              </tr>
              <tr>
                <th>RIGHT_SHOULDER_BOTTOM</th>
                <td>{gamepad.RIGHT_SHOULDER_BOTTOM?.value}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="s4">
          <table className="stripes">
            <tbody>
              <tr>
                <th>SELECT</th>
                <td>{gamepad.SELECT?.value}</td>
              </tr>
              <tr>
                <th>START</th>
                <td>{gamepad.START?.value}</td>
              </tr>
              <tr>
                <th>LEFT_ANALOG_BUTTON</th>
                <td>{gamepad.LEFT_ANALOG_BUTTON?.value}</td>
              </tr>
              <tr>
                <th>RIGHT_ANALOG_BUTTON</th>
                <td>{gamepad.RIGHT_ANALOG_BUTTON?.value}</td>
              </tr>
              <tr>
                <th>HOME</th>
                <td>{gamepad.HOME?.value}</td>
              </tr>
              <tr>
                <th>MISCBUTTON_1</th>
                <td>{gamepad.MISCBUTTON_1?.value}</td>
              </tr>
              <tr>
                <th>MISCBUTTON_2</th>
                <td>{gamepad.MISCBUTTON_2?.value}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default GamepadView;
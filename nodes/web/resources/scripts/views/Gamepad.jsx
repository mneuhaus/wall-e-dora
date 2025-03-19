import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import node from '../Node';
import gamepads from '../Gamepads';

const GamepadView = () => {
  const { index } = useParams();
  const [gamepad, setGamepad] = useState(null);
  const [counter, setCounter] = useState(0);
  const gamepadRef = useRef(null);
  
  useEffect(() => {
    // Set initial gamepad if available
    if (gamepads.gamepads[index]) {
      gamepadRef.current = gamepads.gamepads[index];
      setGamepad({...gamepadRef.current});
    }
    
    // Listen for gamepad connection
    const handleGamepadConnected = (connectedGamepad) => {
      if (connectedGamepad.index === parseInt(index)) {
        gamepadRef.current = connectedGamepad;
        setGamepad({...gamepadRef.current});
      }
    };
    
    // Listen for gamepad updates
    const handleGamepadUpdate = (updatedGamepad) => {
      if (updatedGamepad.index === parseInt(index)) {
        gamepadRef.current = updatedGamepad;
        // Force a re-render 
        setCounter(prev => prev + 1);
      }
    };
    
    // Set up event listeners
    gamepads.on('gamepadconnected', handleGamepadConnected);
    
    // Directly subscribe to the gamepad update events
    if (gamepads.gamepads[index]) {
      gamepads.gamepads[index].on('gamepad_update', handleGamepadUpdate);
    }
    
    return () => {
      // Clean up event listeners
      gamepads.off('gamepadconnected', handleGamepadConnected);
      if (gamepads.gamepads[index]) {
        gamepads.gamepads[index].off('gamepad_update', handleGamepadUpdate);
      }
    };
  }, [index]);
  
  // Render current gamepad state on each update
  const renderGamepad = () => {
    if (!gamepadRef.current) return null;
    
    return (
      <div className="controller" style={{ margin: '20px' }}>
        <h6>{gamepadRef.current.id}</h6>
        <div className="grid">
          <div className="s4">
            <table className="stripes">
              <tbody>
                <tr>
                  <th>LEFT_ANALOG_STICK X</th>
                  <td>{gamepadRef.current.LEFT_ANALOG_STICK_X?.value}</td>
                </tr>
                <tr>
                  <th>LEFT_ANALOG_STICK Y</th>
                  <td>{gamepadRef.current.LEFT_ANALOG_STICK_Y?.value}</td>
                </tr>
                <tr>
                  <th>RIGHT_ANALOG_STICK X</th>
                  <td>{gamepadRef.current.RIGHT_ANALOG_STICK_X?.value}</td>
                </tr>
                <tr>
                  <th>RIGHT_ANALOG_STICK Y</th>
                  <td>{gamepadRef.current.RIGHT_ANALOG_STICK_Y?.value}</td>
                </tr>
                <tr>
                  <th>DPAD_UP</th>
                  <td>{gamepadRef.current.DPAD_UP?.value}</td>
                </tr>
                <tr>
                  <th>DPAD_DOWN</th>
                  <td>{gamepadRef.current.DPAD_DOWN?.value}</td>
                </tr>
                <tr>
                  <th>DPAD_LEFT</th>
                  <td>{gamepadRef.current.DPAD_LEFT?.value}</td>
                </tr>
                <tr>
                  <th>DPAD_RIGHT</th>
                  <td>{gamepadRef.current.DPAD_RIGHT?.value}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="s4">
            <table className="stripes">
              <tbody>
                <tr>
                  <th>FACE_1</th>
                  <td>{gamepadRef.current.FACE_1?.value}</td>
                </tr>
                <tr>
                  <th>FACE_2</th>
                  <td>{gamepadRef.current.FACE_2?.value}</td>
                </tr>
                <tr>
                  <th>FACE_3</th>
                  <td>{gamepadRef.current.FACE_3?.value}</td>
                </tr>
                <tr>
                  <th>FACE_4</th>
                  <td>{gamepadRef.current.FACE_4?.value}</td>
                </tr>
                <tr>
                  <th>LEFT_SHOULDER</th>
                  <td>{gamepadRef.current.LEFT_SHOULDER?.value}</td>
                </tr>
                <tr>
                  <th>RIGHT_SHOULDER</th>
                  <td>{gamepadRef.current.RIGHT_SHOULDER?.value}</td>
                </tr>
                <tr>
                  <th>LEFT_SHOULDER_BOTTOM</th>
                  <td>{gamepadRef.current.LEFT_SHOULDER_BOTTOM?.value}</td>
                </tr>
                <tr>
                  <th>RIGHT_SHOULDER_BOTTOM</th>
                  <td>{gamepadRef.current.RIGHT_SHOULDER_BOTTOM?.value}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="s4">
            <table className="stripes">
              <tbody>
                <tr>
                  <th>SELECT</th>
                  <td>{gamepadRef.current.SELECT?.value}</td>
                </tr>
                <tr>
                  <th>START</th>
                  <td>{gamepadRef.current.START?.value}</td>
                </tr>
                <tr>
                  <th>LEFT_ANALOG_BUTTON</th>
                  <td>{gamepadRef.current.LEFT_ANALOG_BUTTON?.value}</td>
                </tr>
                <tr>
                  <th>RIGHT_ANALOG_BUTTON</th>
                  <td>{gamepadRef.current.RIGHT_ANALOG_BUTTON?.value}</td>
                </tr>
                <tr>
                  <th>HOME</th>
                  <td>{gamepadRef.current.HOME?.value}</td>
                </tr>
                <tr>
                  <th>MISCBUTTON_1</th>
                  <td>{gamepadRef.current.MISCBUTTON_1?.value}</td>
                </tr>
                <tr>
                  <th>MISCBUTTON_2</th>
                  <td>{gamepadRef.current.MISCBUTTON_2?.value}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };
  
  if (!gamepadRef.current) {
    return (
      <div className="controller" style={{ margin: '20px' }}>
        <h3>Gamepad {index} Not Connected</h3>
        <p>Please connect a gamepad and make sure it's recognized by the browser.</p>
      </div>
    );
  }
  
  return renderGamepad();
};

export default GamepadView;
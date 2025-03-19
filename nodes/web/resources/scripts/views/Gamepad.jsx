import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import node from '../Node';
import gamepads from '../Gamepads';

const GamepadView = () => {
  const { index } = useParams();
  const [, forceUpdate] = useState({});
  const [gamepadInstance, setGamepadInstance] = useState(null);
  
  // Force re-render function that we'll register with the gamepad
  const handleForceUpdate = useCallback(() => {
    forceUpdate({});
  }, []);
  
  useEffect(() => {
    // Set initial gamepad if available
    if (gamepads.gamepads[index]) {
      setGamepadInstance(gamepads.gamepads[index]);
      
      // Register for force updates when gamepad data changes
      const unregister = gamepads.gamepads[index].registerForceUpdate(handleForceUpdate);
      
      return () => {
        // Clean up
        unregister();
      };
    }
    
    // Listen for gamepad connection
    const handleGamepadConnected = (connectedGamepad) => {
      if (connectedGamepad.index === parseInt(index)) {
        setGamepadInstance(connectedGamepad);
        
        // Register for force updates
        const unregister = connectedGamepad.registerForceUpdate(handleForceUpdate);
        
        // Clean up previous registration if component unmounts before this cleanup runs
        return () => {
          unregister();
        };
      }
    };
    
    // Set up event listener
    gamepads.on('gamepadconnected', handleGamepadConnected);
    
    return () => {
      // Clean up event listener
      gamepads.off('gamepadconnected', handleGamepadConnected);
    };
  }, [index, handleForceUpdate]);
  
  if (!gamepadInstance) {
    return (
      <div className="controller" style={{ margin: '20px' }}>
        <h3>Gamepad {index} Not Connected</h3>
        <p>Please connect a gamepad and make sure it's recognized by the browser.</p>
      </div>
    );
  }
  
  return (
    <div className="controller" style={{ margin: '20px' }}>
      <h6>{gamepadInstance.id}</h6>
      <div className="grid">
        <div className="s4">
          <table className="stripes">
            <tbody>
              <tr>
                <th>LEFT_ANALOG_STICK X</th>
                <td>{gamepadInstance.LEFT_ANALOG_STICK_X?.value}</td>
              </tr>
              <tr>
                <th>LEFT_ANALOG_STICK Y</th>
                <td>{gamepadInstance.LEFT_ANALOG_STICK_Y?.value}</td>
              </tr>
              <tr>
                <th>RIGHT_ANALOG_STICK X</th>
                <td>{gamepadInstance.RIGHT_ANALOG_STICK_X?.value}</td>
              </tr>
              <tr>
                <th>RIGHT_ANALOG_STICK Y</th>
                <td>{gamepadInstance.RIGHT_ANALOG_STICK_Y?.value}</td>
              </tr>
              <tr>
                <th>DPAD_UP</th>
                <td>{gamepadInstance.DPAD_UP?.value}</td>
              </tr>
              <tr>
                <th>DPAD_DOWN</th>
                <td>{gamepadInstance.DPAD_DOWN?.value}</td>
              </tr>
              <tr>
                <th>DPAD_LEFT</th>
                <td>{gamepadInstance.DPAD_LEFT?.value}</td>
              </tr>
              <tr>
                <th>DPAD_RIGHT</th>
                <td>{gamepadInstance.DPAD_RIGHT?.value}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="s4">
          <table className="stripes">
            <tbody>
              <tr>
                <th>FACE_1</th>
                <td>{gamepadInstance.FACE_1?.value}</td>
              </tr>
              <tr>
                <th>FACE_2</th>
                <td>{gamepadInstance.FACE_2?.value}</td>
              </tr>
              <tr>
                <th>FACE_3</th>
                <td>{gamepadInstance.FACE_3?.value}</td>
              </tr>
              <tr>
                <th>FACE_4</th>
                <td>{gamepadInstance.FACE_4?.value}</td>
              </tr>
              <tr>
                <th>LEFT_SHOULDER</th>
                <td>{gamepadInstance.LEFT_SHOULDER?.value}</td>
              </tr>
              <tr>
                <th>RIGHT_SHOULDER</th>
                <td>{gamepadInstance.RIGHT_SHOULDER?.value}</td>
              </tr>
              <tr>
                <th>LEFT_SHOULDER_BOTTOM</th>
                <td>{gamepadInstance.LEFT_SHOULDER_BOTTOM?.value}</td>
              </tr>
              <tr>
                <th>RIGHT_SHOULDER_BOTTOM</th>
                <td>{gamepadInstance.RIGHT_SHOULDER_BOTTOM?.value}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="s4">
          <table className="stripes">
            <tbody>
              <tr>
                <th>SELECT</th>
                <td>{gamepadInstance.SELECT?.value}</td>
              </tr>
              <tr>
                <th>START</th>
                <td>{gamepadInstance.START?.value}</td>
              </tr>
              <tr>
                <th>LEFT_ANALOG_BUTTON</th>
                <td>{gamepadInstance.LEFT_ANALOG_BUTTON?.value}</td>
              </tr>
              <tr>
                <th>RIGHT_ANALOG_BUTTON</th>
                <td>{gamepadInstance.RIGHT_ANALOG_BUTTON?.value}</td>
              </tr>
              <tr>
                <th>HOME</th>
                <td>{gamepadInstance.HOME?.value}</td>
              </tr>
              <tr>
                <th>MISCBUTTON_1</th>
                <td>{gamepadInstance.MISCBUTTON_1?.value}</td>
              </tr>
              <tr>
                <th>MISCBUTTON_2</th>
                <td>{gamepadInstance.MISCBUTTON_2?.value}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default GamepadView;